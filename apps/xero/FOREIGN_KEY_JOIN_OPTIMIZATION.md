# Fastest Ways to Do Foreign Key Joins for Changes

## Overview

When checking for changes in related models via foreign keys, Django ORM provides several optimization techniques. This guide shows the fastest methods.

## 1. `select_related()` - Single SQL JOIN (Fastest for ForeignKey)

**Use for**: ForeignKey and OneToOneField relationships  
**How it works**: Performs SQL JOIN in a single query  
**Best for**: When you need the related object's data

### Example: Checking Journal Changes with Transaction Source

```python
# ❌ SLOW: N+1 queries (1 query per journal)
journals = XeroJournals.objects.filter(organisation=org)
for journal in journals:
    source = journal.transaction_source  # Separate query per journal!
    if source.transaction_source == 'Invoice':
        # ...

# ✅ FAST: Single query with JOIN
journals = XeroJournals.objects.select_related('transaction_source').filter(organisation=org)
for journal in journals:
    source = journal.transaction_source  # Already loaded, no query!
    if source.transaction_source == 'Invoice':
        # ...
```

### Multiple Foreign Keys

```python
# ✅ Multiple foreign keys in one query
journals = XeroJournals.objects.select_related(
    'transaction_source',
    'transaction_source__contact',  # Nested foreign key
    'account',
    'organisation'
).filter(organisation=org)
```

## 2. `prefetch_related()` - Separate Optimized Query (For Reverse Relations)

**Use for**: Reverse ForeignKey, ManyToManyField  
**How it works**: Executes 2 queries total (main + related)  
**Best for**: When you need reverse relationships

### Example: Getting All Journals for a Transaction Source

```python
# ❌ SLOW: N+1 queries
sources = XeroTransactionSource.objects.filter(organisation=org)
for source in sources:
    journals = source.journals.all()  # Separate query per source!

# ✅ FAST: 2 queries total
sources = XeroTransactionSource.objects.prefetch_related('journals').filter(organisation=org)
for source in sources:
    journals = source.journals.all()  # Already prefetched!
```

### Prefetch with Filtering

```python
# ✅ Prefetch with filtering (still only 2 queries)
from django.db.models import Prefetch

sources = XeroTransactionSource.objects.prefetch_related(
    Prefetch(
        'journals',
        queryset=XeroJournals.objects.filter(date__gte=some_date),
        to_attr='recent_journals'
    )
).filter(organisation=org)
```

## 3. `only()` and `defer()` - Limit Fields Loaded

**Use for**: When you only need specific fields  
**How it works**: Reduces data transferred from database

### Example: Only Load Needed Fields

```python
# ❌ Loads all fields (slower, more memory)
journals = XeroJournals.objects.select_related('transaction_source').all()

# ✅ Only loads specified fields (faster, less memory)
journals = XeroJournals.objects.select_related('transaction_source').only(
    'journal_id',
    'date',
    'transaction_source__transactions_id',
    'transaction_source__transaction_source'
).filter(organisation=org)
```

### Defer Unnecessary Fields

```python
# ✅ Load all fields except heavy ones
journals = XeroJournals.objects.select_related('transaction_source').defer(
    'collection',  # Large JSONField
    'description'  # Long text field
)
```

## 4. `values()` and `values_list()` - Get Only What You Need

**Use for**: When you only need specific field values  
**How it works**: Returns dicts/lists instead of model instances (much faster)

### Example: Checking for Changes

```python
# ❌ Loads full model instances (slower)
journals = XeroJournals.objects.select_related('transaction_source').all()
changes = []
for journal in journals:
    if journal.transaction_source.transaction_source == 'Invoice':
        changes.append(journal.journal_id)

# ✅ Only loads needed fields (much faster)
journals = XeroJournals.objects.select_related('transaction_source').values(
    'journal_id',
    'transaction_source__transaction_source'
)
changes = [
    j['journal_id'] 
    for j in journals 
    if j['transaction_source__transaction_source'] == 'Invoice'
]
```

### Values List (Even Faster)

```python
# ✅ Fastest: Returns flat list
journal_ids = XeroJournals.objects.filter(
    transaction_source__transaction_source='Invoice'
).values_list('journal_id', flat=True)
```

## 5. `F()` Expressions - Database-Level Operations

**Use for**: Comparing fields or doing calculations in database  
**How it works**: Executes comparison in SQL, not Python

### Example: Finding Changed Records

```python
from django.db.models import F

# ✅ Compare fields in database (single query)
changed_journals = XeroJournals.objects.filter(
    transaction_source__transaction_source=F('journal_source')
).select_related('transaction_source')

# ✅ Update based on foreign key field
XeroJournals.objects.filter(
    transaction_source__transaction_source='Invoice'
).update(status='processed')
```

## 6. Bulk Operations - Avoid Individual Queries

**Use for**: Creating/updating multiple records  
**How it works**: Single query for multiple operations

### Example: Bulk Update Based on Foreign Key

```python
# ❌ SLOW: Individual updates
journals = XeroJournals.objects.select_related('transaction_source').filter(...)
for journal in journals:
    if journal.transaction_source.transaction_source == 'Invoice':
        journal.status = 'processed'
        journal.save()  # Separate query per journal!

# ✅ FAST: Bulk update
XeroJournals.objects.filter(
    transaction_source__transaction_source='Invoice'
).update(status='processed')
```

## 7. Combined Optimization - Best Practices

### Pattern: Check Changes Efficiently

```python
from django.db.models import F, Q, Prefetch

# ✅ Optimized query for checking changes
def get_changed_journals(organisation, since_date=None):
    queryset = XeroJournals.objects.select_related(
        'transaction_source',
        'transaction_source__contact',
        'account'
    ).only(
        'journal_id',
        'date',
        'amount',
        'transaction_source__transactions_id',
        'transaction_source__transaction_source',
        'account__account_id'
    ).filter(organisation=organisation)
    
    if since_date:
        queryset = queryset.filter(updated_at__gte=since_date)
    
    # Use F() for database-level comparisons
    return queryset.filter(
        Q(transaction_source__transaction_source__in=['Invoice', 'Payment']) |
        Q(amount__gt=F('previous_amount'))
    )
```

### Pattern: Detect Changes Between Related Models

```python
# ✅ Fast: Compare related fields in database
from django.db.models import Case, When, Value

changed_records = XeroJournals.objects.select_related('transaction_source').annotate(
    source_type_matches=Case(
        When(transaction_source__transaction_source='Invoice', then=Value(True)),
        default=Value(False)
    )
).filter(source_type_matches=True)
```

## 8. Performance Comparison

### Scenario: Get 1000 journals with their transaction sources

| Method | Queries | Time | Memory |
|--------|---------|------|--------|
| No optimization | 1001 | ~2s | High |
| `select_related()` | 1 | ~0.1s | Medium |
| `select_related()` + `only()` | 1 | ~0.05s | Low |
| `values()` | 1 | ~0.03s | Very Low |

## 9. Real-World Example: Checking Transaction Source Changes

```python
def check_transaction_source_changes(organisation, since_date=None):
    """
    Efficiently check for changes in transaction sources.
    """
    # Build optimized queryset
    queryset = XeroJournals.objects.select_related(
        'transaction_source',
        'transaction_source__contact'
    ).only(
        'journal_id',
        'date',
        'transaction_source__transactions_id',
        'transaction_source__transaction_source',
        'transaction_source__contact__name'
    ).filter(organisation=organisation)
    
    if since_date:
        queryset = queryset.filter(updated_at__gte=since_date)
    
    # Get only changed records (using values for speed)
    changes = queryset.values(
        'journal_id',
        'transaction_source__transaction_source',
        'transaction_source__contact__name'
    ).filter(
        transaction_source__transaction_source__in=['Invoice', 'Payment', 'BankTransaction']
    )
    
    return list(changes)  # Convert to list to evaluate query
```

## 10. Common Mistakes to Avoid

### ❌ Don't: Access Foreign Key Without select_related

```python
journals = XeroJournals.objects.all()
for journal in journals:
    source = journal.transaction_source  # N+1 queries!
```

### ✅ Do: Use select_related

```python
journals = XeroJournals.objects.select_related('transaction_source').all()
for journal in journals:
    source = journal.transaction_source  # Already loaded!
```

### ❌ Don't: Filter After Loading

```python
journals = XeroJournals.objects.select_related('transaction_source').all()
filtered = [j for j in journals if j.transaction_source.transaction_source == 'Invoice']
```

### ✅ Do: Filter in Query

```python
journals = XeroJournals.objects.select_related('transaction_source').filter(
    transaction_source__transaction_source='Invoice'
)
```

## 11. Debugging Query Performance

### Check Query Count

```python
from django.db import connection
from django.test.utils import override_settings

# Before query
initial_queries = len(connection.queries)

# Your code
journals = XeroJournals.objects.select_related('transaction_source').all()
list(journals)  # Evaluate queryset

# After query
final_queries = len(connection.queries)
print(f"Queries executed: {final_queries - initial_queries}")
```

### Use django-debug-toolbar

Install and use Django Debug Toolbar to see all queries executed.

## Summary: Fastest Methods

1. **For ForeignKey**: Use `select_related()` - Single SQL JOIN
2. **For Reverse FK**: Use `prefetch_related()` - 2 optimized queries
3. **For Field Values Only**: Use `values()` or `values_list()` - No model instantiation
4. **For Comparisons**: Use `F()` expressions - Database-level operations
5. **For Updates**: Use `bulk_update()` or `update()` - Single query
6. **For Limited Fields**: Use `only()` or `defer()` - Less data transfer

**Fastest overall**: `select_related()` + `values()` + `F()` expressions for database-level filtering.


"""
GitHub webhook handler for automatic deployment.
"""
import hmac
import hashlib
import subprocess
import logging
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json

logger = logging.getLogger(__name__)


def verify_github_signature(payload_body, signature_header):
    """
    Verify that the payload was sent from GitHub by validating SHA256.
    
    Args:
        payload_body: Raw request body
        signature_header: X-Hub-Signature-256 header value
        
    Returns:
        bool: True if signature is valid
    """
    if not signature_header:
        return False
    
    # Get webhook secret from settings
    webhook_secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', None)
    if not webhook_secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not set in settings. Webhook verification disabled.")
        return True  # Allow if secret not configured (for development)
    
    # Extract signature from header (format: sha256=<signature>)
    hash_object = hmac.new(
        webhook_secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


@csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([AllowAny])
def github_webhook(request):
    """
    GitHub webhook endpoint for automatic deployment.
    
    This endpoint:
    1. Verifies the webhook signature
    2. Checks if it's a push to main branch
    3. Pulls latest code from GitHub
    4. Installs dependencies if requirements.txt changed
    5. Runs migrations if migrations changed
    6. Collects static files
    7. Restarts gunicorn service
    
    Expected GitHub webhook payload:
    {
        "ref": "refs/heads/main",
        "repository": {
            "name": "klikk_financials_v3"
        },
        "commits": [...]
    }
    """
    # Get signature from header
    signature = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    
    # Get raw body for signature verification
    payload_body = request.body
    
    # Verify signature
    if not verify_github_signature(payload_body, signature):
        logger.warning("Invalid webhook signature. Request rejected.")
        return HttpResponseForbidden("Invalid signature")
    
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        return HttpResponse("Invalid JSON", status=400)
    
    # Check if this is a push to main branch
    ref = payload.get('ref', '')
    if ref != 'refs/heads/main':
        logger.info(f"Ignoring webhook for ref: {ref}")
        return Response({
            "message": f"Ignored: not main branch (ref: {ref})",
            "status": "ignored"
        })
    
    # Check repository name
    repo_name = payload.get('repository', {}).get('name', '')
    if repo_name != 'klikk_financials_v3':
        logger.info(f"Ignoring webhook for repository: {repo_name}")
        return Response({
            "message": f"Ignored: wrong repository (name: {repo_name})",
            "status": "ignored"
        })
    
    # Get commit info
    commits = payload.get('commits', [])
    commit_count = len(commits)
    latest_commit = commits[-1] if commits else {}
    commit_message = latest_commit.get('message', 'Unknown')
    commit_author = latest_commit.get('author', {}).get('name', 'Unknown')
    
    logger.info(f"Received webhook: {commit_count} commit(s) to main branch by {commit_author}")
    logger.info(f"Latest commit: {commit_message[:100]}")
    
    # Run deployment script
    try:
        import os
        project_root = settings.BASE_DIR
        # Try server deploy script first, fallback to root deploy script
        deploy_script = os.path.join(project_root, 'scripts', 'server', 'deploy.sh')
        if not os.path.exists(deploy_script):
            deploy_script = os.path.join(project_root, 'scripts', 'deploy.sh')
        
        # Check if deploy script exists
        if not os.path.exists(deploy_script):
            logger.error(f"Deployment script not found: {deploy_script}")
            return Response({
                "message": "Deployment script not found",
                "status": "error"
            }, status=500)
        
        # Execute deployment script
        result = subprocess.run(
            ['bash', deploy_script],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info("Deployment completed successfully")
            return Response({
                "message": "Deployment successful",
                "status": "success",
                "commits": commit_count,
                "latest_commit": commit_message[:100],
                "output": result.stdout
            })
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return Response({
                "message": "Deployment failed",
                "status": "error",
                "error": result.stderr,
                "output": result.stdout
            }, status=500)
            
    except subprocess.TimeoutExpired:
        logger.error("Deployment script timed out")
        return Response({
            "message": "Deployment timed out",
            "status": "error"
        }, status=500)
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}", exc_info=True)
        return Response({
            "message": f"Deployment error: {str(e)}",
            "status": "error"
        }, status=500)

#!/bin/sh
set -e

echo "PR Guardian - Starting initialization..."

# Configure SSH for git operations
if [ -f /root/.ssh/id_ed25519 ]; then
    # Try to set permissions (may fail if read-only mount)
    chmod 600 /root/.ssh/id_ed25519 2>/dev/null || true
    git config --global core.sshCommand "ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/root/.ssh/known_hosts"
    echo "SSH deploy key configured"
fi

# Configure git user for commits
git config --global user.name "PR Guardian Bot"
git config --global user.email "pr-guardian@users.noreply.github.com"

# Import GPG key if using traditional signing
if [ "$SIGNING_METHOD" = "gpg" ] && [ -f /secrets/gpg_bot_key ]; then
    echo "Importing GPG key..."
    gpg --batch --import /secrets/gpg_bot_key 2>/dev/null

    # Get key ID and configure git
    GPG_KEY_ID=$(gpg --list-secret-keys --keyid-format LONG 2>/dev/null | grep sec | head -1 | awk '{print $2}' | cut -d'/' -f2)

    if [ -n "$GPG_KEY_ID" ]; then
        git config --global user.signingkey "$GPG_KEY_ID"
        git config --global commit.gpgsign true
        git config --global gpg.program gpg

        # Configure GPG for non-interactive use
        mkdir -p ~/.gnupg
        echo "use-agent" >> ~/.gnupg/gpg.conf
        echo "pinentry-mode loopback" >> ~/.gnupg/gpg.conf
        chmod 700 ~/.gnupg
        chmod 600 ~/.gnupg/gpg.conf

        echo "GPG signing configured with key: $GPG_KEY_ID"
    else
        echo "Warning: GPG key import failed - no key ID found"
    fi
fi

# Verify GitHub CLI authentication
if [ -n "$GH_TOKEN" ]; then
    if gh auth status >/dev/null 2>&1; then
        echo "GitHub CLI authenticated successfully"
    else
        echo "Warning: GitHub CLI authentication may not be configured correctly"
    fi
else
    echo "Warning: GH_TOKEN environment variable not set"
fi

# Verify Anthropic API key (for LLM integration)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "Anthropic API key configured"
else
    echo "Warning: ANTHROPIC_API_KEY not set - LLM parsing will fail"
fi

echo "Initialization complete. Executing command..."

# Execute main command
exec "$@"

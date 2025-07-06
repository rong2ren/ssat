gh auth status
gh auth switch
gh auth login

gh auth setup-git
- Configures Git to use gh as its credential helper for HTTPS operations.
- Ensures Git uses the same token as the active gh session (via gh auth switch).
- Solves conflicts where git pull/git push use the wrong account credentials.
check using below:

git config --global --get credential.helper
# Should return: !gh auth git-credential

# Fetch your GitHub username via the CLI token
curl -H "Authorization: Bearer $(gh auth token)" https://api.github.com/user

Use gh repo clone instead of git clone to ensure repo ownership aligns with gh’s active account.

Above are only for HTTPs.
SSH will be different.


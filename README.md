# mabuhive

## Running Development Environment 
### Setting up: 
- 1. Get SSH Key:
   ` 
    eval "$(ssh-agent -s)"
    ssh-add ~/.ssh/id_ed25519  # or id_rsa
   `
- 2. Run `./scripts/dev.sh`
- 3. In container, run `ssh -T git@github.com`
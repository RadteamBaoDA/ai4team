#!/bin/bash
# download_models.sh - Download LLM Guard models for local usage

set -e

# Configuration
MODELS_DIR=${LLM_GUARD_MODELS_PATH:-./models}
DRY_RUN=${DRY_RUN:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to download a model
download_model() {
    local repo_url="$1"
    local local_name="$2"
    local description="$3"
    
    log_info "Downloading $description..."
    log_info "  Repository: $repo_url"
    log_info "  Local path: $MODELS_DIR/$local_name"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_warning "DRY RUN: Would download $repo_url to $local_name"
        return 0
    fi
    
    if [ -d "$MODELS_DIR/$local_name" ]; then
        log_warning "Directory $local_name already exists, skipping download"
        return 0
    fi
    
    cd "$MODELS_DIR"
    
    if git clone "$repo_url" "$local_name"; then
        log_success "Downloaded $description"
    else
        log_error "Failed to download $description"
        return 1
    fi
    
    # Check if model files exist
    if [ -f "$local_name/config.json" ]; then
        log_success "Model configuration found"
    else
        log_warning "Model configuration not found - download may be incomplete"
    fi
}

# Function to check disk space
check_disk_space() {
    local required_space_gb=10  # Estimate 10GB for all models
    local available_space_gb
    
    if command_exists df; then
        # Get available space in GB
        available_space_gb=$(df "$MODELS_DIR" | awk 'NR==2 {printf "%.1f", $4/1024/1024}' 2>/dev/null || echo "unknown")
        
        if [ "$available_space_gb" != "unknown" ] && [ "$(echo "$available_space_gb < $required_space_gb" | bc -l 2>/dev/null || echo "0")" = "1" ]; then
            log_warning "Low disk space detected. Available: ${available_space_gb}GB, Recommended: ${required_space_gb}GB"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Aborted due to disk space concerns"
                exit 1
            fi
        else
            log_info "Disk space check: ${available_space_gb}GB available"
        fi
    else
        log_warning "Cannot check disk space (df command not available)"
    fi
}

# Function to setup git LFS
setup_git_lfs() {
    log_info "Setting up Git LFS..."
    
    if ! command_exists git; then
        log_error "Git is not installed. Please install git first."
        exit 1
    fi
    
    if ! command_exists git-lfs; then
        log_error "Git LFS is not installed. Please install git-lfs first."
        log_info "Installation instructions:"
        log_info "  Ubuntu/Debian: sudo apt install git-lfs"
        log_info "  CentOS/RHEL: sudo yum install git-lfs"
        log_info "  macOS: brew install git-lfs"
        exit 1
    fi
    
    if [ "$DRY_RUN" != "true" ]; then
        git lfs install
        log_success "Git LFS initialized"
    else
        log_warning "DRY RUN: Would initialize Git LFS"
    fi
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Download LLM Guard models for local usage"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -d, --dir DIR       Set models directory (default: ./models)"
    echo "  --dry-run           Show what would be done without actually doing it"
    echo "  --check-only        Only check prerequisites, don't download"
    echo ""
    echo "Environment Variables:"
    echo "  LLM_GUARD_MODELS_PATH   Models directory path"
    echo "  DRY_RUN                 Set to 'true' for dry run"
    echo ""
    echo "Examples:"
    echo "  $0                      # Download to ./models"
    echo "  $0 -d /opt/models       # Download to /opt/models"
    echo "  $0 --dry-run            # Show what would be downloaded"
    echo "  LLM_GUARD_MODELS_PATH=/data/models $0  # Use environment variable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "LLM Guard Models Download Script"
    log_info "================================"
    log_info "Models directory: $MODELS_DIR"
    log_info "Dry run: $DRY_RUN"
    echo ""
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    setup_git_lfs
    
    # Create models directory
    if [ "$DRY_RUN" != "true" ]; then
        mkdir -p "$MODELS_DIR"
        log_success "Created models directory: $MODELS_DIR"
    else
        log_warning "DRY RUN: Would create directory $MODELS_DIR"
    fi
    
    # Check disk space
    check_disk_space
    
    if [ "${CHECK_ONLY:-false}" = "true" ]; then
        log_info "Prerequisites check completed successfully"
        exit 0
    fi
    
    echo ""
    log_info "Starting model downloads..."
    echo ""
    
    # Download models
    # Model definitions: URL, local_name, description
    models=(
        "https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2 deberta-v3-base-prompt-injection-v2 PromptInjection_Scanner_Model"
        "https://huggingface.co/unitary/unbiased-toxic-roberta unbiased-toxic-roberta Toxicity_Scanner_Model"
        "https://huggingface.co/philomath-1209/programming-language-identification programming-language-identification Code_Scanner_Model"
        "https://huggingface.co/Isotonic/deberta-v3-base_finetuned_ai4privacy_v2 deberta-v3-base_finetuned_ai4privacy_v2 Anonymize_Scanner_Model"
    )
    
    failed_downloads=0
    
    for model_info in "${models[@]}"; do
        # Parse model info
        read -r repo_url local_name description <<< "$model_info"
        
        if ! download_model "$repo_url" "$local_name" "$description"; then
            ((failed_downloads++))
        fi
        echo ""
    done
    
    # Summary
    echo ""
    log_info "Download Summary"
    log_info "==============="
    
    total_models=${#models[@]}
    successful_downloads=$((total_models - failed_downloads))
    
    log_info "Total models: $total_models"
    log_info "Successful downloads: $successful_downloads"
    
    if [ $failed_downloads -gt 0 ]; then
        log_error "Failed downloads: $failed_downloads"
    fi
    
    if [ "$DRY_RUN" != "true" ] && [ $failed_downloads -eq 0 ]; then
        echo ""
        log_success "All models downloaded successfully!"
        log_info "You can now enable local models with:"
        log_info "  export LLM_GUARD_USE_LOCAL_MODELS=true"
        log_info "  export LLM_GUARD_MODELS_PATH=$MODELS_DIR"
        
        # Show disk usage
        if command_exists du; then
            total_size=$(du -sh "$MODELS_DIR" 2>/dev/null | cut -f1 || echo "unknown")
            log_info "Total disk usage: $total_size"
        fi
        
        echo ""
        log_info "To test the configuration, run:"
        log_info "  python test_local_models.py"
        
    elif [ "$DRY_RUN" = "true" ]; then
        echo ""
        log_info "Dry run completed. No files were downloaded."
        log_info "Run without --dry-run to actually download the models."
        
    else
        echo ""
        log_error "Some downloads failed. Please check the errors above and retry."
        exit 1
    fi
}

# Run main function
main "$@"
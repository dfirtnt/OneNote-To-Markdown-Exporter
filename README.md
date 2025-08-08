# OneNote to Markdown Exporter

A powerful CLI tool that exports OneNote notebooks to Markdown files with embedded images. Uses Microsoft Graph API with device code flow authentication.

## Features

- ✅ Export entire OneNote notebooks to organized Markdown files
- ✅ Preserve notebook structure (sections and pages)
- ✅ Download and embed images inline
- ✅ Handle rate limiting with exponential backoff
- ✅ Comprehensive error handling and logging
- ✅ Support for personal Microsoft accounts
- ✅ Clean, organized output structure

## Prerequisites

- Python 3.7+
- Microsoft account with OneNote notebooks
- Azure AD application registration (for API access)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/dfirtnt/OneNote-To-Markdown-Exporter.git
cd OneNote-To-Markdown-Exporter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Azure AD application:
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to "Azure Active Directory" > "App registrations"
   - Click "New registration"
   - Name: "OneNote Exporter" (or any name)
   - Supported account types: "Personal Microsoft accounts only"
   - Redirect URI: (leave blank)
   - Click "Register"
   - Copy the "Application (client) ID"

4. Configure API permissions:
   - In your app registration, go to "API permissions"
   - Click "Add a permission"
   - Select "Microsoft Graph" > "Delegated permissions"
   - Add: `Notes.Read.All` and `User.Read`
   - Click "Grant admin consent"

## Configuration

### Option 1: Environment Variable (Recommended)
```bash
export ONENOTE_CLIENT_ID="your-client-id-here"
```

### Option 2: Direct Configuration
Edit the `CLIENT_ID` variable in the script files (not recommended for security).

## Usage

### Basic Export
```bash
python onenote_exporter.py
```

This will:
- Authenticate using device code flow
- Discover all your OneNote notebooks
- Export them to the `output/` directory
- Preserve the notebook structure

### Debug Token
Test your authentication and permissions:
```bash
python debug_token.py
```

### Test Permissions
Verify API access:
```bash
python test_permissions.py
```

## Output Structure

```
output/
├── Notebook Name/
│   ├── Section Name/
│   │   ├── page1.md
│   │   ├── page2.md
│   │   └── images/
│   │       ├── image1.png
│   │       └── image2.jpg
│   └── Another Section/
│       └── page3.md
└── Another Notebook/
    └── ...
```

## Security Considerations

- **Never commit your CLIENT_ID to version control**
- Use environment variables for sensitive configuration
- The `output/` directory contains your exported data - review before sharing
- Log files may contain sensitive information - they're excluded from git

## Troubleshooting

### Authentication Issues
- Ensure your Azure AD app has the correct permissions
- Verify you're using a personal Microsoft account
- Check that the CLIENT_ID is correct

### Rate Limiting
The tool automatically handles rate limiting with exponential backoff. If you encounter issues:
- Wait a few minutes before retrying
- Check the log file for detailed error information

### Media Download Issues
Some images may fail to download due to API limitations. The export will continue with placeholder references.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for personal use and educational purposes. Please respect Microsoft's terms of service and API usage limits.

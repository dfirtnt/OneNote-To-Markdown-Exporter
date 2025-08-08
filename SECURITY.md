# Security Guide

This document outlines security considerations for the OneNote to Markdown Exporter.

## 🔒 Sensitive Data Handling

### What's Been Secured

✅ **Client ID**: Removed hardcoded client ID from all files
✅ **Environment Variables**: Added support for `ONENOTE_CLIENT_ID` environment variable
✅ **Configuration**: Created `config_example.py` for safe configuration examples
✅ **Gitignore**: Excluded sensitive files and directories

### Files to Review Before Publishing

1. **Check for any remaining hardcoded credentials**:
   ```bash
   grep -r "34eaf836-3a99-43f6-8b51-e127d16c7bb2" .
   ```

2. **Verify .gitignore excludes sensitive data**:
   - `output/` - Contains exported OneNote data
   - `*.log` - May contain sensitive information
   - `config.py` - User-specific configuration
   - `.env` - Environment variables

3. **Review exported content**:
   - Check `output/` directory for any personal/sensitive information
   - Remove or anonymize any personal data before publishing

## 🛡️ Security Best Practices

### For Users

1. **Use Environment Variables**:
   ```bash
   export ONENOTE_CLIENT_ID="your-client-id-here"
   ```

2. **Never commit credentials**:
   - Don't add `config.py` with real credentials
   - Don't commit `.env` files
   - Don't hardcode client IDs in scripts

3. **Review exported data**:
   - Check `output/` directory before sharing
   - Remove any sensitive personal information

### For Contributors

1. **Test with dummy data**:
   - Use test notebooks for development
   - Don't commit real exported content

2. **Follow security guidelines**:
   - Always use environment variables for secrets
   - Don't log sensitive information
   - Handle errors without exposing internal details

## 🔍 Pre-Publish Checklist

- [ ] No hardcoded client IDs in any files
- [ ] All sensitive files excluded in .gitignore
- [ ] Output directory contains no personal data
- [ ] Log files don't contain sensitive information
- [ ] README includes security considerations
- [ ] Configuration examples use placeholders
- [ ] Environment variable usage documented

## 🚨 Security Contacts

If you discover a security vulnerability, please:
1. **Do not** create a public issue
2. Contact the maintainer privately
3. Allow time for assessment and fix

## 📋 Compliance

This tool:
- Uses Microsoft Graph API with proper authentication
- Respects Microsoft's terms of service
- Implements rate limiting to avoid API abuse
- Handles user data responsibly

## 🔐 Data Privacy

- No data is sent to external services (except Microsoft Graph API)
- All processing happens locally
- No telemetry or analytics collection
- User data remains under user control

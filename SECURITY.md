# Security Policy

## Supported Versions

We take security seriously and actively maintain security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Comfy Gimpy Studio, please help us by reporting it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:
- **security@comfy-gimpy.dev**

### What to Include

When reporting a vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Impact**: Potential impact and severity of the vulnerability
4. **Environment**: Your environment details (OS, Python version, etc.)
5. **Contact Information**: How we can reach you for follow-up questions

### Our Response Process

1. **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
2. **Investigation**: We will investigate the report and determine its validity
3. **Updates**: We will provide regular updates on our progress (at least weekly)
4. **Fix**: If valid, we will work on a fix and coordinate disclosure
5. **Disclosure**: We will publicly disclose the vulnerability after a fix is available

### Disclosure Policy

- We follow a 90-day disclosure timeline from initial report
- We will credit researchers who responsibly disclose vulnerabilities
- We will not pursue legal action against researchers who follow this policy

## Security Considerations

### For Users

- Always download from official sources
- Keep dependencies updated
- Use strong, unique passwords for any accounts
- Be cautious with marketplace packs from untrusted sources

### For Contributors

- Never commit sensitive information (API keys, passwords, etc.)
- Use secure coding practices
- Validate all inputs
- Follow the principle of least privilege

## Known Security Considerations

### Image Processing
- Large images may consume significant memory
- Malformed image files could cause crashes
- Always validate image inputs before processing

### Network Operations
- API calls to external services should use HTTPS
- Implement proper timeout handling
- Validate SSL certificates

### File Operations
- Validate file paths to prevent directory traversal
- Check file sizes before processing
- Use secure temporary file creation

### Marketplace Packs
- Only install packs from trusted sources
- Review pack contents before installation
- Be aware of potential malicious code in custom packs

## Security Updates

Security updates will be:
- Released as patch versions (1.0.x)
- Documented in release notes
- Announced through our communication channels
- Backported to supported versions when applicable

## Contact

For security-related questions or concerns:
- Email: security@comfy-gimpy.dev
- General inquiries: info@comfy-gimpy.dev

Thank you for helping keep Comfy Gimpy Studio secure! 🛡️
# Security Policy

## Supported Versions

The following versions of Tile-Crawler are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Tile-Crawler seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Send a detailed report to the project maintainers via:
   - GitHub Security Advisories (preferred): [Report a vulnerability](https://github.com/kase1111-hash/Tile-Crawler/security/advisories/new)
   - Direct contact through GitHub

### What to Include

Please include the following information in your report:

- **Description**: A clear description of the vulnerability
- **Impact**: Potential impact and severity assessment
- **Reproduction Steps**: Detailed steps to reproduce the issue
- **Affected Components**: Which parts of the system are affected
- **Suggested Fix**: If you have recommendations for remediation

### Response Timeline

- **Initial Response**: Within 48 hours of report
- **Status Update**: Within 7 days with assessment
- **Resolution Target**: Critical issues within 30 days

### What to Expect

1. **Acknowledgment**: We will acknowledge receipt of your report
2. **Investigation**: We will investigate and validate the vulnerability
3. **Communication**: We will keep you informed of our progress
4. **Credit**: With your permission, we will credit you in the security advisory

## Security Considerations

### Authentication

- JWT-based authentication with secure token handling
- Password hashing using bcrypt via Passlib
- Token expiration and refresh mechanisms

### API Security

- CORS configuration for allowed origins
- Input validation using Pydantic models
- Rate limiting recommended for production deployments

### Database

- Parameterized queries to prevent SQL injection
- Support for PostgreSQL with connection pooling
- SQLite for development/testing

### LLM Integration

- API keys stored in environment variables
- No sensitive data included in LLM prompts
- Response sanitization before rendering

### Environment Variables

The following sensitive configuration should be protected:

| Variable | Description |
| -------- | ----------- |
| `OPENAI_API_KEY` | OpenAI API authentication |
| `JWT_SECRET` | JWT signing secret |
| `DATABASE_URL` | Database connection string |

### Deployment Recommendations

1. **HTTPS**: Always use HTTPS in production
2. **Environment Variables**: Never commit secrets to version control
3. **Firewall**: Restrict database access to application servers only
4. **Updates**: Keep dependencies updated for security patches
5. **Monitoring**: Implement logging and monitoring for suspicious activity

## Known Security Limitations

- **LLM Content**: AI-generated content may contain unexpected outputs
- **Local Storage**: Browser local storage used for some client-side data
- **WebSocket**: Real-time connections should be secured with WSS in production

## Security Updates

Security updates will be announced through:

- GitHub Security Advisories
- Release notes in CHANGELOG.md
- Repository releases

## Acknowledgments

We appreciate the security research community's efforts in responsibly disclosing vulnerabilities. Contributors who report valid security issues will be acknowledged (with permission) in our security advisories.

Thank you for helping keep Tile-Crawler secure!

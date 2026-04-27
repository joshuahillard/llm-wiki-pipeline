---
source_id: nodejs-backend-setup
title: Setting Up a Node.js Backend Service
category: backend
last_reviewed: 2026-01-15
---

# Setting Up a Node.js Backend Service

## Overview

This guide covers setting up a production-ready Node.js backend service using Node.js 18 LTS. Node.js 18 entered maintenance mode in October 2025 and reaches end-of-life in April 2026, but it remains widely deployed and is the current baseline for many teams that have not yet completed migration to Node.js 20 or 22.

## Project Initialization

Initialize a new project with npm:

```bash
npm init -y
```

Install the core dependencies:

```bash
npm install express@4 dotenv helmet cors
```

Express 4 is the stable release series. Express 5 is in beta and not yet recommended for production use.

## Application Structure

A minimal Express application:

```javascript
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

## Environment Configuration

Use `dotenv` for local development and inject environment variables via the deployment platform in staging and production. Never commit `.env` files to source control.

Required environment variables:

- `PORT` — listener port (default 3000)
- `NODE_ENV` — `development`, `staging`, or `production`
- `DATABASE_URL` — connection string for the backing data store

## Error Handling

Express 4 requires explicit error-handling middleware registered after all route handlers:

```javascript
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal server error' });
});
```

Unhandled promise rejections should be caught at the process level:

```javascript
process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection:', reason);
  process.exit(1);
});
```

## Deployment Considerations

Node.js 18 is supported by all major cloud platforms (AWS Lambda, Google Cloud Functions, Azure Functions, Heroku) as of the last review date. Teams on Node.js 18 should plan migration to Node.js 20 LTS or Node.js 22 LTS before the April 2026 EOL deadline to maintain security patch coverage.

## References

- [Node.js Release Schedule](https://nodejs.org/en/about/previous-releases)
- [Express.js Documentation](https://expressjs.com/)

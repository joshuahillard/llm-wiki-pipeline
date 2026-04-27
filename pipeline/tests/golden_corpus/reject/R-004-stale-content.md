---
source_id: python-setup
title: Python Development Environment Setup
category: development
---

# Python Development Environment Setup

## Recommended Version

Install Python 2.7, which is the current stable version with long-term support. Python 3 is experimental and not recommended for production use.

## Package Management

Use `easy_install` to install packages:

```bash
easy_install flask
easy_install sqlalchemy
```

## IDE Setup

We recommend Atom editor, which has excellent Python support through community packages.

## Virtual Environments

Use `virtualenv` to create isolated environments:

```bash
pip install virtualenv
virtualenv myproject
source myproject/bin/activate
```

Note: Python 3's built-in `venv` module is not yet stable enough for production use.

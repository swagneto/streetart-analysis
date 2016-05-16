# Acquiring <code>client_secret.json</code>

The Graffiti Project uses the installed application model (or web
authorization, or server-side authorization, as it's called) which requires
some identifying information and a shared secret to authenticate.  Since
this is tied to a developer's account for resource accounting, and potential
billing, it is not provided as part of the repository but rather expected
to be created before use.

**NOTE:** These instructions are current as of 2016/05/16.

The administrator of the project (read: developer) manages everything at:

  https://console.developers.google.com/apis/library

# Project Configuration

## Create a Project

**NOTE:** This step may be skipped if the administrator wishes to add the
 Graffiti Project into an existing project.

1. Create a new project.  This can be found in a drop down on the top bar.
2. Give it a project name.  This is for management purposes and isn't what is
shown to the end users.
3. Agree to the Terms of Service.

## Enable the Drive API

**NOTE:** This step may be skipped if the Drive API has already been added to
an existing project.

1. Navigate to the "Overview" section on the left-hand side.
2. Navigate to the Drive API link and enable it.

## Create Credentials

1. Navigate to the "Credentials" section on the left-hand side.
2. Create a product name under the "OAuth consent screen" tab.  Fill in
  "Product name shown to users" with something identifiable.  This will be shown to users when
  they allow the Graffiti Project's tools to access their Google Drive.
3. Save.
4. Create a client secret under the "Credentials" tab.  Click the "Create
  credentials" button, select "OAuth client id", "Other" as the
  application type, and then name the credentials (doesn't matter to what).

## Install Credentials Locally
1. Download it via the "Download JSON" link on the Credentials page.
2. Move it to <code>~/.credentials/graffiti-analysis-client-secret.json</code>.

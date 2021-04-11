#!/usr/bin/env python3

from aws_cdk import core

from cdk.personal_website_stack import PersonalWebsiteStack

app = core.App()

PersonalWebsiteStack(app, "PersonalWebsite",
                     stack_name="PersonalWebsite",
                     termination_protection=True,
                     domain_name="crmyers.dev",
                     tags={"project": "personal-site"},
                     description="Stack for my personal static website")
app.synth()

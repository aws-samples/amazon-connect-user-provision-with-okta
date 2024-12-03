#!/usr/bin/env python3
from aws_cdk import App
from okta_connector_app.okta_connector_stack import OktaConnectorStack

app = App()

# Create the stack and synthesize the CloudFormation template
OktaConnectorStack(app, "OktaConnectorStack")
app.synth()

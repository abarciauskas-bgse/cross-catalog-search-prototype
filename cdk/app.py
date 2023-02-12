#!/usr/bin/env python3
import os

from aws_cdk import core

from cdk.lambda_stack import LambdaStack

app = core.App()

env_details = core.Environment(
    region=os.environ["CDK_DEFAULT_REGION"],
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
)

APP_NAME = 'cross-catalog-search'
ENV = 'def'
lambda_stack = LambdaStack(
    app,
    f"{APP_NAME}-{ENV}-lambda",
    env=env_details,
)

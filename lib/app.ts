#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { PhotoHostingStack } from "./PhotoHostingStack";

const app = new cdk.App();

new PhotoHostingStack(app, "PhotoHostingStack", {
    stackName: "PhotoHostingStack",
    env: {
        region: "us-east-1"
    }
});

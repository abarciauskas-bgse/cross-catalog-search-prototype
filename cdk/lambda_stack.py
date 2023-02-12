from aws_cdk import (
    core,
    aws_lambda,
    aws_lambda_python,
    aws_iam as iam,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_events, aws_events_targets
)

class LambdaStack(core.Stack):
    def __init__(self, app, construct_id, **kwargs) -> None:
        super().__init__(app, construct_id, **kwargs)
        self.construct_id = construct_id

        # Generates URLs from cmr and MAAP
        self.gen_urls_lambda = self._lambda(
            f"{construct_id}-gen_urls", "../lambdas/gen_urls"
        )
        rule = aws_events.Rule(
            self,
            "Rule",
            schedule=aws_events.Schedule.expression("cron(0 0 * * ? *)"),
        )
        rule.add_target(aws_events_targets.LambdaFunction(self.gen_urls_lambda))        

    def _lambda(
        self,
        name,
        dir,
        memory_size=1024,
        timeout_seconds=900,
        env=None,
        reserved_concurrent_executions=None,
        **kwargs,
    ):
        return aws_lambda.Function(
            self,
            name,
            function_name=name,
            code=aws_lambda.Code.from_asset_image(
                directory=dir,
                file="Dockerfile",
                entrypoint=["/usr/local/bin/python", "-m", "awslambdaric"],
                cmd=["handler.handler"],
            ),
            handler=aws_lambda.Handler.FROM_IMAGE,
            runtime=aws_lambda.Runtime.FROM_IMAGE,
            memory_size=memory_size,
            timeout=core.Duration.seconds(timeout_seconds),
            environment=env,
            reserved_concurrent_executions=reserved_concurrent_executions,
            **kwargs,
        )

    def _python_lambda(self, name, directory, env=None, timeout_seconds=900, **kwargs):
        return aws_lambda_python.PythonFunction(
            self,
            name,
            function_name=name,
            entry=directory,
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            index="handler.py",
            handler="handler",
            environment=env,
            timeout=core.Duration.seconds(timeout_seconds),
            **kwargs,
        )

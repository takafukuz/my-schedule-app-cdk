import aws_cdk as core
import aws_cdk.assertions as assertions

from my_schedule_app_cdk.my_schedule_app_cdk_stack import MyScheduleAppCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in my_schedule_app_cdk/my_schedule_app_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MyScheduleAppCdkStack(app, "my-schedule-app-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

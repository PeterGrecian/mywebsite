from pprint import pprint

def lambda_handler(event, context):
    html_file = open("cv.html", 'r')
    html = html_file.read()
    content = f'<body><html>{html}</html></body>'
    print("-------------------event")
    pprint(event)
    print("-------------------contect")
    pprint(context)
    print("-------------------end")
    return {
        'statusCode': 200,
        "body": content,
        "headers": {
            'Content-Type': 'text/html',
        }
    }

if __name__ == "__main__":
    lambda_handler("", "")

from pprint import pprint, pformat


def lambda_handler(event, context):
    html = ""
    favicon=open("favicon.png64", "r").read()

    fav = f'<title>CV</title><link rel="icon" type="image/png" href="data:image/png;base64,{favicon}">'
    path = event['path']
    stage = event['requestContext']['stage']
    host = event['headers']['Host']
    root=f'https://{host}/{stage}'

    if path.endswith("event"):
        html += context.log_group_name + "<br>"
        html += context.log_stream_name + "<br>" 
        html += event['path'] + "<br>"
        html += stage + "<br>"
        for key in event.keys():
            html += "_______________________" + key + "_________________________<br>"
            html += pformat(event[key])   + "<br><br>"            
        html += pformat(event)
        html += "________________________________________________<br>"
        content = f'<html><head>{fav}</head>{html}<body></body></html>'
    elif path.endswith("contents"):
        html += '<table border="1">'
        html += f"<tr><td><a href={root}/contents>{root}/contents</a></td><td>this document</tr>"
        html += f"<tr><td><a href={root}/anything>{root}/<i>anything else</a></td><td>my CV</i></tr>"
        html += f"<tr><td><a href={root}/event>{root}/event</a></td><td>the event and context of the lambda_handler</tr>"
        html += f"</table>"
    else:
        html += open("cv.html", 'r').read()
 
    content = f'<html><head>{fav}</head><body>{html}</body></html>'
    return {
        'statusCode': 200,
        "body": content,
        "headers": {
            'Content-Type': 'text/html',
        }
    }

if __name__ == "__main__":
    lambda_handler("", "")

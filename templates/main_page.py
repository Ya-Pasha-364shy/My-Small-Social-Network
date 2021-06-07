from fastapi.responses import HTMLResponse


def generate_html_response():
    main_sourse = """
        <html>
            <head>
                <title>Some HTML in here</title>
            </head>
            <body>
                <h1>Look ma! HTML!</h1>
            </body>
        </html>
    """
    return HTMLResponse(content=main_sourse, status_code=200)

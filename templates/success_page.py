from fastapi.responses import HTMLResponse


def success_letter(letter: str):
    html_content = f"""
    <html>
        <head>
            <title>{letter}</title>
        </head>
        <body>
            <h1>Have fun!</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

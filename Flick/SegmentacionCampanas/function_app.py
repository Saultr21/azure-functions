import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="segmentar_campana", methods=["POST"])
def segmentar_campana(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("not implemented", status_code=501)

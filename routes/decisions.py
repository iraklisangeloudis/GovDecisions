from flask import Blueprint, jsonify, redirect, render_template, request

from services.diavgeia import DiavgeiaError, diavgeia, document_url

decisions_bp = Blueprint("decisions", __name__)


def search_parameters():
    supervised = request.args.get("include_supervised", "false").lower()
    if supervised not in {"true", "false"}:
        raise ValueError("include_supervised must be true or false.")
    try:
        page = int(request.args.get("page", "0"))
        size = int(request.args.get("size", "20"))
    except ValueError as exc:
        raise ValueError("page and size must be integers.") from exc
    return {
        "org": request.args.get("org"),
        "page": page,
        "size": size,
        "include_supervised": supervised == "true",
    }


@decisions_bp.route("/")
def index():
    return render_template("index.html")


@decisions_bp.route("/api/organizations")
def organizations():
    try:
        return jsonify(diavgeia.ministries())
    except DiavgeiaError as exc:
        return jsonify(error=str(exc)), 503


@decisions_bp.route("/api/decisions")
def decisions():
    try:
        params = search_parameters()
        if params["org"] is None:
            return jsonify(decisions=[], page=0, size=20, total=0, hasMore=False, stale=False)
        return jsonify(diavgeia.decisions(**params))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except DiavgeiaError as exc:
        return jsonify(error=str(exc)), 503


@decisions_bp.route("/download/<ada>")
def download_pdf(ada):
    # PDFs remain accessible even when their decision is no longer on page one.
    return redirect(document_url(ada))

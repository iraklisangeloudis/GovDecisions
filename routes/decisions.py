import json

from flask import Blueprint, jsonify, redirect, render_template, request, send_file

from services.diavgeia import DiavgeiaError, diavgeia, document_url
from services.documents import DocumentError, fetch_pdf

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
    try:
        extra = json.loads(request.args.get("extra", "{}"))
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid special filters.") from exc
    return {
        **{key: request.args.get(key, "") for key in
           ("term", "ada", "protocol", "issue_from", "issue_to", "updated_from", "updated_to")},
        "status": request.args.get("status", "published"),
        "extra": extra,
        "org": request.args.get("org"),
        "page": page,
        "size": size,
        "include_supervised": supervised == "true",
        "decision_type": request.args.get("type", ""),
        "thematic_category": request.args.get("tag", ""),
    }


@decisions_bp.route("/")
def index():
    return render_template("index.html")


@decisions_bp.route("/api/organizations")
def organizations():
    try:
        return jsonify(diavgeia.organizations_by_category(request.args.get("category", "MINISTRY")))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
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


@decisions_bp.route("/api/filters")
def filters():
    try:
        return jsonify(diavgeia.filters())
    except DiavgeiaError as exc:
        return jsonify(error=str(exc)), 503


@decisions_bp.route("/api/special-filters")
def special_filters():
    try:
        return jsonify(diavgeia.special_fields(request.args.get("type", "")))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except DiavgeiaError as exc:
        return jsonify(error=str(exc)), 503


@decisions_bp.route("/api/filter-dictionary")
def filter_dictionary():
    try:
        return jsonify(diavgeia.dictionary(request.args.get("name", "")))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except DiavgeiaError as exc:
        return jsonify(error=str(exc)), 503


@decisions_bp.route("/document/<ada>")
def preview_pdf(ada):
    try:
        pdf, length = fetch_pdf(ada)
    except DocumentError as exc:
        return jsonify(error=str(exc)), exc.status_code
    try:
        response = send_file(pdf, mimetype="application/pdf", download_name=f"{ada}.pdf",
                             as_attachment=False, conditional=False, etag=False)
        response.content_length = length
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        response.call_on_close(pdf.close)
        return response
    except Exception:
        pdf.close()
        raise


@decisions_bp.route("/download/<ada>")
def download_pdf(ada):
    # PDFs remain accessible even when their decision is no longer on page one.
    return redirect(document_url(ada))

import random
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import func, or_
from models import Problem, UserProblem, Category, ProblemCategory
from functools import wraps
from problems.sync import load_all_problems_once, incremental_sync_from_current_size
from flask import abort
from extensions import limiter
from flask_login import login_required, current_user

problems_bp = Blueprint("problems", __name__)

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)
    return wrapper

@problems_bp.route("/admin/load-problems-once", methods=["POST"])
@admin_required
@limiter.limit("2 per hour")
def load_problems_once_route():
    added = load_all_problems_once()
    return {"added": added}

@problems_bp.route("/admin/sync-problems", methods=["POST"])
@admin_required
@limiter.limit("2 per hour")
def sync_problems_route():
    added = incremental_sync_from_current_size()
    return {"added": added}

@problems_bp.route("/add-problems", methods=["GET", "POST"])
@limiter.limit("20 per minute")
@login_required
def add_problems():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()

    if request.method == "POST":
        action = request.form.get("action", "fetch")
        problem_number = request.form.get("problem_number", "").strip()

        if action == "fetch":
            if not problem_number.isdigit():
                flash("Enter a valid problem number.", "danger")
                return render_template("add_problems.html", categories=categories, problem=None, confirm=False)

            problem = Problem.query.filter_by(id=int(problem_number)).first()
            if not problem:
                flash("Problem not found in database.", "danger")
                return render_template("add_problems.html", categories=categories, problem=None, confirm=False)

            return render_template(
                "add_problems.html",
                categories=categories,
                problem=problem,
                confirm=True
            )

        if action == "save":
            problem_id = request.form.get("problem_id", "").strip()
            if not problem_id.isdigit():
                flash("Invalid problem.", "danger")
                return redirect(url_for("problems.add_problems"))

            problem = Problem.query.get(int(problem_id))
            if not problem:
                flash("Problem not found.", "danger")
                return redirect(url_for("problems.add_problems"))

            categories_selected = request.form.getlist("categories")
            custom_category = request.form.get("custom_category", "").strip()

            user_problem = UserProblem.query.filter_by(user_id=current_user.id, problem_id=problem.id).first()
            if not user_problem:
                user_problem = UserProblem(user_id=current_user.id, problem_id=problem.id)
                db.session.add(user_problem)
                db.session.flush()

            selected_names = [c.strip() for c in categories_selected if c.strip()]
            if custom_category:
                selected_names.append(custom_category)

            if selected_names:
                for name in selected_names:
                    category = Category.query.filter_by(user_id=current_user.id, name=name).first()
                    if not category:
                        category = Category(user_id=current_user.id, name=name)
                        db.session.add(category)
                        db.session.flush()

                    existing_link = ProblemCategory.query.filter_by(
                        user_problem_id=user_problem.id,
                        category_id=category.id
                    ).first()

                    if not existing_link:
                        db.session.add(ProblemCategory(
                            user_problem_id=user_problem.id,
                            category_id=category.id
                        ))

                db.session.commit()
                flash(f"Added '{problem.title}' with selected categories.", "success")
            else:
                db.session.commit()
                flash(f"Added '{problem.title}' as uncategorized.", "success")

            return redirect(url_for("problems.add_problems"))

    solved = (
        db.session.query(UserProblem, Problem)
        .join(Problem, UserProblem.problem_id == Problem.id)
        .filter(UserProblem.user_id == current_user.id)
        .order_by(UserProblem.created_at.desc())
        .all()
    )

    return render_template("add_problems.html", categories=categories, problem=None, confirm=False, solved=solved)

@problems_bp.route("/solve-problems", methods=["GET", "POST"])
@limiter.limit("5 per minute")
@login_required
def solve_problems():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()
    selected_ids = []
    selected_problems = []

    if request.method == "POST":
        selected_category_ids = request.form.getlist("category_ids")
        if selected_category_ids:
            selected_ids = [int(x) for x in selected_category_ids if x.isdigit()]
            for cid in selected_ids:
                matched = (
                    db.session.query(UserProblem, Problem)
                    .join(Problem, UserProblem.problem_id == Problem.id)
                    .join(ProblemCategory, ProblemCategory.user_problem_id == UserProblem.id)
                    .filter(UserProblem.user_id == current_user.id, ProblemCategory.category_id == cid)
                    .all()
                )
                if matched:
                    chosen = random.choice(matched)
                    cat = db.session.get(Category, cid)
                    selected_problems.append({
                        "title": chosen.Problem.title,
                        "link": chosen.Problem.link,
                        "problem_number": chosen.Problem.leetcode_problem_id,
                        "category": cat.name if cat else "Category"
                    })
        else:
            all_solved = (
                db.session.query(UserProblem, Problem)
                .join(Problem, UserProblem.problem_id == Problem.id)
                .filter(UserProblem.user_id == current_user.id)
                .all()
            )
            if all_solved:
                chosen = random.choice(all_solved)
                selected_problems.append({
                    "title": chosen.Problem.title,
                    "link": chosen.Problem.link,
                    "problem_number": chosen.Problem.leetcode_problem_id,
                    "category": "Any"
                })

        unique = {}
        for item in selected_problems:
            unique[item["problem_number"]] = item
        selected_problems = list(unique.values())

    return render_template(
        "solve_problems.html",
        categories=categories,
        selected_category_ids=selected_ids,
        selected_problems=selected_problems
    )

@problems_bp.route("/manage-problems", methods=["GET"])
@limiter.limit("20 per minute")
@login_required
def manage_problems():
    q = request.args.get("q", "").strip()

    query = (
        db.session.query(UserProblem, Problem)
        .join(Problem, UserProblem.problem_id == Problem.id)
        .filter(UserProblem.user_id == current_user.id)
    )

    if q:
        like_q = f"%{q}%"

        # search by title, problem number, or category name
        query = query.outerjoin(ProblemCategory, ProblemCategory.user_problem_id == UserProblem.id)\
                     .outerjoin(Category, Category.id == ProblemCategory.category_id)\
                     .filter(
                         or_(
                             Problem.title.ilike(like_q),
                             func.cast(Problem.leetcode_problem_id, db.String).ilike(like_q),
                             Category.name.ilike(like_q),
                         )
                     )

    solved_rows = query.order_by(UserProblem.created_at.desc()).all()

    solved_problems = []
    for up, problem in solved_rows:
        category_names = [
            pc.category.name
            for pc in up.categories
            if pc.category is not None
        ]
        solved_problems.append({
            "user_problem_id": up.id,
            "problem_number": problem.leetcode_problem_id,
            "title": problem.title,
            "link": problem.link,
            "categories": category_names
        })

    return render_template("manage_problems.html", solved_problems=solved_problems, q=q)


@problems_bp.route("/edit-solved-problem/<int:user_problem_id>", methods=["GET", "POST"])
@limiter.limit("20 per minute")
@login_required
def edit_solved_problem(user_problem_id):
    user_problem = UserProblem.query.filter_by(id=user_problem_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        categories = request.form.getlist("categories")
        custom_category = request.form.get("custom_category", "").strip()

        selected_names = [c.strip() for c in categories if c.strip()]
        if custom_category:
            selected_names.append(custom_category)

        # remove old category links
        ProblemCategory.query.filter_by(user_problem_id=user_problem.id).delete()

        # add new category links
        if selected_names:
            for name in selected_names:
                category = Category.query.filter_by(user_id=current_user.id, name=name).first()
                if not category:
                    category = Category(user_id=current_user.id, name=name)
                    db.session.add(category)
                    db.session.flush()

                link = ProblemCategory.query.filter_by(
                    user_problem_id=user_problem.id,
                    category_id=category.id
                ).first()

                if not link:
                    db.session.add(ProblemCategory(
                        user_problem_id=user_problem.id,
                        category_id=category.id
                    ))

        db.session.commit()
        flash("Tags updated successfully.", "success")
        return redirect(url_for("problems.manage_problems"))

    problem = user_problem.problem
    current_categories = [
        pc.category.name
        for pc in user_problem.categories
        if pc.category is not None
    ]
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()

    return render_template(
        "edit_solved_problem.html",
        user_problem=user_problem,
        problem=problem,
        categories=categories,
        current_categories=current_categories
    )


@problems_bp.route("/delete-solved-problem/<int:user_problem_id>", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def delete_solved_problem(user_problem_id):
    user_problem = UserProblem.query.filter_by(id=user_problem_id, user_id=current_user.id).first_or_404()
    db.session.delete(user_problem)
    db.session.commit()
    flash("Solved problem deleted.", "success")
    return redirect(url_for("problems.manage_problems"))


@problems_bp.route("/clear-solved-problems", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def clear_solved_problems():
    solved = UserProblem.query.filter_by(user_id=current_user.id).all()
    for item in solved:
        db.session.delete(item)
    db.session.commit()
    flash("All solved problems cleared.", "success")
    return redirect(url_for("problems.manage_problems"))

@problems_bp.route("/clear-all-categories", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def clear_all_categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    for category in categories:
        db.session.delete(category)
    db.session.commit()
    flash("All categories cleared.", "success")
    return redirect(url_for("problems.manage_problems"))

@problems_bp.route("/api/health")
def health():
    return jsonify({"status": "ok"})

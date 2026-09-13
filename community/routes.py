from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import User, UserProblem, Problem, ProblemCategory, Category
from extensions import db

community_bp = Blueprint("community", __name__)

@community_bp.route("/users")
@login_required
def users_list():
    users = (
        User.query
        .filter(User.id != current_user.id)
        .order_by(User.username.asc())
        .all()
    )
    return render_template("users_list.html", users=users)

@community_bp.route("/users/<int:user_id>")
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)

    solved_rows = (
        db.session.query(UserProblem, Problem)
        .join(Problem, UserProblem.problem_id == Problem.id)
        .filter(UserProblem.user_id == user.id)
        .order_by(UserProblem.created_at.desc())
        .all()
    )

    solved_problems = []
    for up, problem in solved_rows:
        category_names = [
            pc.category.name
            for pc in up.categories
            if pc.category is not None
        ]
        solved_problems.append({
            "problem_number": problem.leetcode_problem_id,
            "title": problem.title,
            "link": problem.link,
            "categories": category_names
        })

    return render_template(
        "user_profile.html",
        user=user,
        solved_problems=solved_problems
    )
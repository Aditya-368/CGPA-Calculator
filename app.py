from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # IMPORTANT: Change this to a random, long string!

# --- Helper Functions ---

def get_user_grading_system(user_id):
    """Fetches the grading system for a specific user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT grade_letter, grade_point FROM grading_systems WHERE user_id = ?", (user_id,))
    grading_system_rows = cursor.fetchall()
    db.close()
    
    grading_system_map = {row['grade_letter'].upper(): row['grade_point'] for row in grading_system_rows}
    return grading_system_map

def get_grade_letter_from_point(user_grading_system, point):
    """
    Given a grade point, finds the corresponding grade letter from the user's grading system.
    Assumes points are sorted descendingly in the system.
    """
    if not user_grading_system:
        return "N/A" # No grading system defined

    # Sort grade letters by their points in descending order
    sorted_grades = sorted(user_grading_system.items(), key=lambda item: item[1], reverse=True)

    for letter, grade_point in sorted_grades:
        if point >= grade_point:
            return letter
    
    # If point is lower than any defined grade point, assign the lowest grade letter or F
    lowest_grade_letter = sorted_grades[-1][0] if sorted_grades else "F"
    return lowest_grade_letter


def calculate_course_final_grade(course_id, user_grading_system):
    """Calculates the final grade_point for a course based on its components."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT name, weight, score, max_score FROM course_components WHERE course_id = ?", (course_id,))
    components = cursor.fetchall()
    db.close()

    if not components:
        return None, None # Cannot calculate if no components

    total_weighted_score = 0
    total_weight = 0

    for comp in components:
        if comp['score'] is not None and comp['max_score'] is not None and comp['max_score'] > 0:
            percentage = (comp['score'] / comp['max_score']) * 100
            total_weighted_score += (percentage * comp['weight'])
            total_weight += comp['weight']
        else:
            # If a component is missing score/max_score, we can't fully calculate weighted average.
            # You might want to handle this differently (e.g., skip it, return error).
            pass # For now, we'll just skip components with missing data

    if total_weight == 0:
        return None, None # Avoid division by zero, if no valid components contributed

    # The result here is a percentage (e.g., 85.5) which we need to convert to grade point
    final_percentage = total_weighted_score / total_weight
    
    # Convert percentage to a 4.0 scale using the user's grading system
    # This requires a more nuanced mapping or defining what a 100% means in terms of grade points.
    # For now, let's simplify: map 100% to the highest grade point in the user's system
    # and 0% to the lowest. This is an approximation.
    
    # More accurate: map based on user's defined grade ranges, but that requires ranges.
    # For now, we'll assume a direct conversion to grade point scale based on the system.
    
    # Let's simplify and just use the percentage as a proxy for now
    # This part needs careful thought if you want exact 4.0 scale conversion from percentage
    # For this beginner example, let's assume `final_grade_point` is just the scaled percentage
    # or that the 'grade_point' in the grading system is already percentage based for simplicity.

    # A better way for mapping: treat `grade_point` values in grading_systems as the 4.0 scale directly.
    # The percentage calculated here (0-100) needs to be converted to one of those grade letters,
    # then to its point.

    # Option 1: Convert percentage to an approximated grade point (rough)
    # This is a highly simplified direct mapping.
    # Example: If A=4.0, B=3.0. A 90% might be 4.0, 80% might be 3.0.
    # This would require defining numerical cutoffs for grades.
    # For initial implementation, let's store the raw percentage as `final_grade_point` and convert
    # it to a letter grade *only for display*, and use a simpler numeric mapping for CGPA.
    
    # Let's convert the percentage to a grade point based on the highest defined in user's system
    # This still isn't ideal without knowing explicit percentage cutoffs for each grade letter.

    # For now, let's return the percentage directly and let the CGPA logic use it,
    # and map it to a grade letter from the system.
    # This implies that a user's 'grade_point' for 'A' is the numerical value for 100%
    # and their 'F' is 0%. This is likely not what they intend.

    # A more robust approach would be to have grade_systems define *ranges* or a lookup function.
    # For now, let's assume `grade_point` in grading_systems are already on a 4.0 scale,
    # and our calculated `final_percentage` needs to map to one of those letters.
    
    # Let's assume a linear mapping: Highest grade_point maps to 100%, lowest to 0%.
    # This is still a simplification.
    
    # Let's get the numeric grade based on components, and then assign a letter from the user's system.
    # Assuming standard percentage to letter mapping (e.g., 90-100=A, 80-89=B etc.)
    # and then lookup that letter in the user's grading system.
    
    # Let's refine `get_grade_point_from_percentage_and_system` or similar.
    # For now, if components are used, let's return a calculated numerical score (percentage 0-100)
    # and then map that to a letter and then to a grade point from the user's defined system.

    # Simplified approach: If a course is component-based, its `final_grade_point` will be a direct conversion
    # of the percentage to a grade letter point *using the user's system*.
    
    # Example conversion:
    # 90-100% -> A, 80-89% -> B, etc.
    # Then lookup A's grade point from `user_grading_system`.
    
    # Let's implement this simplified conversion.
    # This needs to be consistent with how user's define their grade letters.
    # For example, if A+ is 4.0, and 95% gets A+, then 4.0 is the grade point.
    
    # This `_calculate_grade_point_from_percentage` helper is crucial.
    
    # A temporary fixed percentage-to-letter mapping for component calculations (this can be customizable later):
    letter_from_percentage = ""
    if final_percentage >= 90: letter_from_percentage = "A"
    elif final_percentage >= 80: letter_from_percentage = "B"
    elif final_percentage >= 70: letter_from_percentage = "C"
    elif final_percentage >= 60: letter_from_percentage = "D"
    else: letter_from_percentage = "F"
    
    # Try to get the specific grade letter point if defined, else use generic A/B/C
    grade_point_from_components = None
    if letter_from_percentage in user_grading_system:
        grade_point_from_components = user_grading_system[letter_from_percentage]
    else:
        # Fallback if generic letter (A,B,C) isn't in user's system.
        # This highlights the need for a customizable percentage-to-letter mapping.
        # For now, use the raw percentage scaled to max grade point if possible
        max_gp = max(user_grading_system.values()) if user_grading_system else 4.0
        grade_point_from_components = (final_percentage / 100.0) * max_gp

    return final_percentage, grade_point_from_components, letter_from_percentage


def calculate_cgpa(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT credits, final_grade_point, calculation_method, id FROM courses WHERE user_id = ?", (user_id,))
    courses = cursor.fetchall()
    db.close()

    user_grading_system = get_user_grading_system(user_id) # Need user's system for component-based calculation

    total_credits = 0
    total_grade_points_sum = 0 # sum of (credits * grade_point)

    for course in courses:
        current_course_grade_point = None

        if course['calculation_method'] == 'components':
            # Calculate grade point from components
            percentage_score, calculated_grade_point, _ = calculate_course_final_grade(course['id'], user_grading_system)
            if calculated_grade_point is not None:
                current_course_grade_point = calculated_grade_point
        else: # 'final_grade' method
            if course['final_grade_point'] is not None:
                current_course_grade_point = course['final_grade_point']
        
        if current_course_grade_point is not None:
            total_credits += course['credits']
            total_grade_points_sum += (course['credits'] * current_course_grade_point)

    if total_credits == 0:
        return 0.0
    return round(total_grade_points_sum / total_credits, 2)


# --- Before/After Request Hooks ---

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        g.grading_system = {} # No grading system if not logged in
    else:
        db = get_db()
        cursor = db.cursor()
        g.user = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        db.close()
        g.grading_system = get_user_grading_system(user_id) # Load user's grading system

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# --- Routes ---

@app.route('/')
def index():
    if g.user:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=('GET', 'POST'))
def register():
    if g.user:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            db = get_db()
            cursor = db.cursor()
            try:
                hashed_password = generate_password_hash(password)
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                db.commit()
                
                # --- AUTO-POPULATE DEFAULT GRADING SYSTEM FOR NEW USER ---
                user_id = cursor.lastrowid
                default_grades = {
                    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                    'D+': 1.3, 'D': 1.0,
                    'F': 0.0
                }
                for grade_letter, grade_point in default_grades.items():
                    cursor.execute(
                        "INSERT INTO grading_systems (user_id, grade_letter, grade_point) VALUES (?, ?, ?)",
                        (user_id, grade_letter, grade_point)
                    )
                db.commit()
                # --- END AUTO-POPULATE ---

            except sqlite3.IntegrityError:
                error = f"User {username} is already registered."
            finally:
                db.close()

            if error is None:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))

        flash(error, 'danger')

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if g.user:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None

        db = get_db()
        cursor = db.cursor()
        user = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            flash('You have been logged in!', 'success')
            return redirect(url_for('dashboard'))

        flash(error, 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if g.user is None:
        return redirect(url_for('login'))

    cgpa = calculate_cgpa(g.user['id'])

    return render_template('dashboard.html', cgpa=cgpa)

@app.route('/grading_system', methods=('GET', 'POST'))
def grading_system():
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_or_update':
            grade_letter = request.form['grade_letter'].upper()
            grade_point = float(request.form['grade_point'])

            if not grade_letter or grade_point is None:
                flash('Grade letter and point are required.', 'danger')
            else:
                try:
                    cursor.execute(
                        "INSERT INTO grading_systems (user_id, grade_letter, grade_point) VALUES (?, ?, ?)",
                        (g.user['id'], grade_letter, grade_point)
                    )
                    db.commit()
                    flash(f'Grade "{grade_letter}" added successfully!', 'success')
                except sqlite3.IntegrityError:
                    # If grade_letter already exists for this user, update it
                    cursor.execute(
                        "UPDATE grading_systems SET grade_point = ? WHERE user_id = ? AND grade_letter = ?",
                        (grade_point, g.user['id'], grade_letter)
                    )
                    db.commit()
                    flash(f'Grade "{grade_letter}" updated successfully!', 'success')
                except ValueError:
                    flash('Invalid grade point. Please enter a number.', 'danger')

        elif action == 'delete':
            grade_id = request.form.get('grade_id')
            if grade_id:
                cursor.execute("DELETE FROM grading_systems WHERE id = ? AND user_id = ?", (grade_id, g.user['id']))
                db.commit()
                flash('Grade mapping deleted.', 'info')
            else:
                flash('Invalid grade ID for deletion.', 'danger')
        
        db.close() # Close DB connection after POST
        return redirect(url_for('grading_system'))

    # GET request
    user_grading_system_list = cursor.execute(
        "SELECT id, grade_letter, grade_point FROM grading_systems WHERE user_id = ? ORDER BY grade_point DESC",
        (g.user['id'],)
    ).fetchall()
    db.close()

    return render_template('grading_system.html', grading_system_list=user_grading_system_list)


@app.route('/courses', methods=('GET', 'POST'))
def courses():
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    # Fetch final_grade_letter and final_grade_point now
    user_courses = cursor.execute("SELECT id, name, credits, calculation_method, final_grade_letter, final_grade_point FROM courses WHERE user_id = ?", (g.user['id'],)).fetchall()
    db.close()

    # Pre-calculate component-based course grades for display
    # This loop can be optimized if it becomes slow with many courses
    courses_for_display = []
    for course in user_courses:
        course_data = dict(course) # Convert row to mutable dict
        
        if course_data['calculation_method'] == 'components':
            percentage_score, calculated_grade_point, calculated_grade_letter = calculate_course_final_grade(course_data['id'], g.grading_system)
            course_data['display_grade_letter'] = calculated_grade_letter if calculated_grade_letter else "N/A"
            course_data['display_grade_point'] = "%.2f (%.1f%%)" % (calculated_grade_point, percentage_score) if calculated_grade_point is not None else "N/A"
        else: # final_grade method
            course_data['display_grade_letter'] = course_data['final_grade_letter'] if course_data['final_grade_letter'] else "N/A"
            course_data['display_grade_point'] = "%.2f" % course_data['final_grade_point'] if course_data['final_grade_point'] is not None else "N/A"

        courses_for_display.append(course_data)

    if request.method == 'POST':
        name = request.form['name']
        credits = float(request.form['credits'])
        calculation_method = request.form.get('calculation_method', 'final_grade') # Default to final_grade

        error = None

        if not name or not credits:
            error = 'Course name and credits are required.'

        if calculation_method == 'final_grade':
            grade_letter = request.form['grade_letter'].upper()
            if not grade_letter:
                error = 'Grade letter is required for Final Grade method.'
            elif grade_letter not in g.grading_system: # Use g.grading_system
                error = f'Invalid grade letter "{grade_letter}". Please add it to your grading system first.'
            final_grade_point = g.grading_system[grade_letter] if error is None else None
        else: # 'components' method
            grade_letter = None
            final_grade_point = None # Will be calculated later from components

        if error is None:
            db = get_db()
            cursor = db.cursor()
            try:
                cursor.execute(
                    "INSERT INTO courses (user_id, name, credits, calculation_method, final_grade_letter, final_grade_point) VALUES (?, ?, ?, ?, ?, ?)",
                    (g.user['id'], name, credits, calculation_method, grade_letter, final_grade_point)
                )
                db.commit()
                flash('Course added successfully!', 'success')
                return redirect(url_for('courses'))
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')
            finally:
                db.close()

        flash(error, 'danger')

    available_grades = sorted(g.grading_system.keys(), key=lambda x: g.grading_system[x], reverse=True)
    return render_template('courses.html', courses=courses_for_display, available_grades=available_grades)

@app.route('/edit_course/<int:course_id>', methods=('GET', 'POST'))
def edit_course(course_id):
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    course = cursor.execute("SELECT * FROM courses WHERE id = ? AND user_id = ?", (course_id, g.user['id'])).fetchone()

    if course is None:
        db.close()
        flash('Course not found or you do not have permission to edit it.', 'danger')
        return redirect(url_for('courses'))

    if request.method == 'POST':
        name = request.form['name']
        credits = float(request.form['credits'])
        calculation_method = request.form.get('calculation_method', 'final_grade')

        error = None

        if not name or not credits:
            error = 'Course name and credits are required.'

        final_grade_letter = None
        final_grade_point = None

        if calculation_method == 'final_grade':
            grade_letter_input = request.form['grade_letter'].upper()
            if not grade_letter_input:
                error = 'Grade letter is required for Final Grade method.'
            elif grade_letter_input not in g.grading_system:
                error = f'Invalid grade letter "{grade_letter_input}". Please add it to your grading system first.'
            else:
                final_grade_letter = grade_letter_input
                final_grade_point = g.grading_system[final_grade_letter]
        else: # 'components' method
            # If switching to components, clear existing final grade data
            pass # We don't set final_grade_letter/point here, they'll be derived if components exist.

        if error is None:
            try:
                cursor.execute(
                    "UPDATE courses SET name = ?, credits = ?, calculation_method = ?, final_grade_letter = ?, final_grade_point = ? WHERE id = ? AND user_id = ?",
                    (name, credits, calculation_method, final_grade_letter, final_grade_point, course_id, g.user['id'])
                )
                db.commit()
                flash('Course updated successfully!', 'success')
                db.close()
                return redirect(url_for('courses'))
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')
        
        db.close() # Close DB in case of error too
        flash(error, 'danger')
        # Re-render the form with existing data and error
        available_grades = sorted(g.grading_system.keys(), key=lambda x: g.grading_system[x], reverse=True)
        return render_template('edit_course.html', course=course, available_grades=available_grades)

    # GET request
    db.close() # Close DB connection for GET
    available_grades = sorted(g.grading_system.keys(), key=lambda x: g.grading_system[x], reverse=True)
    return render_template('edit_course.html', course=course, available_grades=available_grades)

@app.route('/delete_course/<int:course_id>', methods=('POST',))
def delete_course(course_id):
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    
    course = cursor.execute("SELECT * FROM courses WHERE id = ? AND user_id = ?", (course_id, g.user['id'])).fetchone()
    if course:
        # Due to ON DELETE CASCADE in schema, components will be deleted automatically.
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        db.commit()
        flash('Course deleted successfully!', 'success')
    else:
        flash('Course not found or you do not have permission to delete it.', 'danger')
    
    db.close()
    return redirect(url_for('courses'))


@app.route('/course/<int:course_id>/components', methods=('GET', 'POST'))
def manage_components(course_id):
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    
    # Verify course belongs to user
    course = cursor.execute(
        "SELECT id, name, credits, calculation_method FROM courses WHERE id = ? AND user_id = ?",
        (course_id, g.user['id'])
    ).fetchone()

    if course is None:
        db.close()
        flash('Course not found or you do not have permission to manage components for it.', 'danger')
        return redirect(url_for('courses'))
    
    # Ensure calculation method is set to 'components'
    if course['calculation_method'] == 'final_grade':
        # Automatically switch to components method if user tries to manage components
        cursor.execute(
            "UPDATE courses SET calculation_method = 'components', final_grade_letter = NULL, final_grade_point = NULL WHERE id = ?",
            (course_id,)
        )
        db.commit()
        flash(f'Calculation method for "{course["name"]}" switched to component-based.', 'info')
        course = cursor.execute("SELECT id, name, credits, calculation_method FROM courses WHERE id = ?", (course_id,)).fetchone() # Re-fetch updated course

    components = cursor.execute(
        "SELECT id, name, weight, score, max_score FROM course_components WHERE course_id = ?",
        (course_id,)
    ).fetchall()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_or_update':
            component_id = request.form.get('component_id') # For editing existing
            name = request.form['name']
            weight = float(request.form['weight'])
            score = float(request.form['score']) if request.form['score'] else None
            max_score = float(request.form.get('max_score', 100.0)) # Default to 100

            if not name or weight is None:
                flash('Component name and weight are required.', 'danger')
            elif weight <= 0:
                flash('Weight must be positive.', 'danger')
            else:
                try:
                    if component_id: # Update existing component
                        cursor.execute(
                            "UPDATE course_components SET name = ?, weight = ?, score = ?, max_score = ? WHERE id = ? AND course_id = ?",
                            (name, weight, score, max_score, component_id, course_id)
                        )
                        flash('Component updated successfully!', 'success')
                    else: # Add new component
                        cursor.execute(
                            "INSERT INTO course_components (course_id, name, weight, score, max_score) VALUES (?, ?, ?, ?, ?)",
                            (course_id, name, weight, score, max_score)
                        )
                        flash('Component added successfully!', 'success')
                    db.commit()
                except ValueError:
                    flash('Invalid input for weight, score, or max score. Please enter numbers.', 'danger')
                except Exception as e:
                    flash(f'Error adding/updating component: {e}', 'danger')

        elif action == 'delete':
            component_id = request.form.get('component_id_to_delete')
            if component_id:
                cursor.execute("DELETE FROM course_components WHERE id = ? AND course_id = ?", (component_id, course_id))
                db.commit()
                flash('Component deleted successfully!', 'info')
            else:
                flash('Invalid component ID for deletion.', 'danger')
        
        # After any POST action, recalculate and update the course's final grade point
        percentage_score, calculated_grade_point, calculated_grade_letter = calculate_course_final_grade(course_id, g.grading_system)
        
        cursor.execute(
            "UPDATE courses SET final_grade_letter = ?, final_grade_point = ? WHERE id = ?",
            (calculated_grade_letter, calculated_grade_point, course_id)
        )
        db.commit()

        db.close()
        return redirect(url_for('manage_components', course_id=course_id))

    # GET request: Display components and current calculated grade
    db.close()
    
    percentage_score, calculated_grade_point, calculated_grade_letter = calculate_course_final_grade(course_id, g.grading_system)
    
    return render_template(
        'manage_components.html',
        course=course,
        components=components,
        calculated_percentage=round(percentage_score, 2) if percentage_score is not None else None,
        calculated_grade_point=round(calculated_grade_point, 2) if calculated_grade_point is not None else None,
        calculated_grade_letter=calculated_grade_letter
    )

@app.route('/delete_component/<int:component_id>', methods=('POST',))
def delete_component(component_id):
    if g.user is None:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    
    component = cursor.execute("SELECT course_id FROM course_components WHERE id = ?", (component_id,)).fetchone()
    if not component:
        db.close()
        flash('Component not found.', 'danger')
        return redirect(request.referrer or url_for('courses'))
    
    course_id = component['course_id']
    course = cursor.execute("SELECT user_id FROM courses WHERE id = ?", (course_id,)).fetchone()

    if course and course['user_id'] == g.user['id']:
        cursor.execute("DELETE FROM course_components WHERE id = ?", (component_id,))
        db.commit()
        flash('Component deleted successfully!', 'success')

        # After deleting, recalculate and update the course's final grade point
        percentage_score, calculated_grade_point, calculated_grade_letter = calculate_course_final_grade(course_id, g.grading_system)
        cursor.execute(
            "UPDATE courses SET final_grade_letter = ?, final_grade_point = ? WHERE id = ?",
            (calculated_grade_letter, calculated_grade_point, course_id)
        )
        db.commit()

    else:
        flash('Component not found or you do not have permission to delete it.', 'danger')
    
    db.close()
    return redirect(url_for('manage_components', course_id=course_id)) # Redirect back to manage components

# Endpoint for AJAX requests (e.g., real-time CGPA calc in JS)
@app.route('/_get_current_cgpa')
def _get_current_cgpa():
    if g.user:
        cgpa = calculate_cgpa(g.user['id'])
        return jsonify(cgpa=cgpa)
    return jsonify(cgpa=0.0) # Or error, depending on desired behavior

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
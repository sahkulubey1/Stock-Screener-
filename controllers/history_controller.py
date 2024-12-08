from flask import render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

class HistoryController:
    def __init__(self):
        pass

    def get_db_connection(self):
        conn = sqlite3.connect('database/database.db')
        conn.row_factory = sqlite3.Row
        return conn

    def history_filter(self, user_id, start_date=None, end_date=None):
        conn = self.get_db_connection()

        # Fetch user data
        user_data = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        user_data = dict(user_data) if user_data else {}

        # Fetch indicator weights and their related results
        if start_date and end_date:
            query = '''
                SELECT * FROM indicator_weights
                WHERE user_id = ? AND created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
            '''
            weights_data = conn.execute(query, (user_id, start_date, end_date)).fetchall()
        else:
            query = '''
                SELECT * FROM indicator_weights
                WHERE user_id = ?
                ORDER BY created_at DESC
            '''
            weights_data = conn.execute(query, (user_id,)).fetchall()

        weights_with_results = []
        for weight in weights_data:
            weight_dict = dict(weight)
            # Fetch only results related to this specific weight
            results_query = '''
                SELECT * FROM indicator_results
                WHERE weight_id = ? ORDER BY created_at DESC
            '''
            results_data = conn.execute(results_query, (weight['id'],)).fetchall()
            results_dict = [dict(result) for result in results_data]
            weights_with_results.append({'weight': weight_dict, 'results': results_dict})

        conn.close()

        return {'user': user_data, 'weights_with_results': weights_with_results}

    def history(self, user_id):
        conn = self.get_db_connection()

        # Fetch user data
        user_data = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        user_data = dict(user_data) if user_data else {}

        # Fetch indicator weights and their related results
        weights_data = conn.execute('SELECT * FROM indicator_weights WHERE user_id = ?', (user_id,)).fetchall()

        weights_with_results = []
        for weight in weights_data:
            weight_dict = dict(weight)
            # Fetch only results related to this specific weight
            results_data = conn.execute(
                'SELECT * FROM indicator_results WHERE weight_id = ? ORDER BY created_at DESC',
                (weight['id'],)
            ).fetchall()
            results_dict = [dict(result) for result in results_data]
            weights_with_results.append({'weight': weight_dict, 'results': results_dict})

        conn.close()

        return {'user': user_data, 'weights_with_results': weights_with_results}

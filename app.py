import os
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": [
    "https://wealthsync-frontend3.onrender.com",
    "http://localhost:3000"
]}})

# In-memory database for budget history
budget_history = []

# Hierarchical economic data: continents -> countries -> cities
# Sample data for brevity; expand to all 195 countries and their cities
economic_data = {
    "africa": {
        "countries": {
            "nigeria": {
                "inflation": 12.0,
                "cost_of_living_index": 25,
                "currency": "NGN",
                "cities": {
                    "lagos": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},  # Higher in major city
                    "abuja": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            },
            "south africa": {
                "inflation": 5.8,
                "cost_of_living_index": 38,
                "currency": "ZAR",
                "cities": {
                    "johannesburg": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2},
                    "cape town": {"inflation_adjustment": 1.0, "cost_of_living_adjustment": 1.1}
                }
            }
        }
    },
    "asia": {
        "countries": {
            "india": {
                "inflation": 5.0,
                "cost_of_living_index": 30,
                "currency": "INR",
                "cities": {
                    "mumbai": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},
                    "delhi": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2},
                    "bangalore": {"inflation_adjustment": 1.0,"cost_of_living_adjustment": 1.4}
                }
            },
            "japan": {
                "inflation": 2.5,
                "cost_of_living_index": 75,
                "currency": "JPY",
                "cities": {
                    "tokyo": {"inflation_adjustment": 1.3, "cost_of_living_adjustment": 1.4},
                    "osaka": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            }
        }
    },
    "europe": {
        "countries": {
            "france": {
                "inflation": 3.0,
                "cost_of_living_index": 63,
                "currency": "EUR",
                "cities": {
                    "paris": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},
                    "lyon": {"inflation_adjustment": 1.0, "cost_of_living_adjustment": 1.1}
                }
            },
            "united kingdom": {
                "inflation": 4.0,
                "cost_of_living_index": 65,
                "currency": "GBP",
                "cities": {
                    "london": {"inflation_adjustment": 1.3, "cost_of_living_adjustment": 1.4},
                    "manchester": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            }
        }
    },
    "north america": {
        "countries": {
            "united states": {
                "inflation": 3.2,
                "cost_of_living_index": 70,
                "currency": "USD",
                "cities": {
                    "new york": {"inflation_adjustment": 1.3, "cost_of_living_adjustment": 1.5},
                    "los angeles": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3}
                }
            },
            "canada": {
                "inflation": 3.5,
                "cost_of_living_index": 62,
                "currency": "CAD",
                "cities": {
                    "toronto": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},
                    "vancouver": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            }
        }
    },
    "south america": {
        "countries": {
            "brazil": {
                "inflation": 6.5,
                "cost_of_living_index": 45,
                "currency": "BRL",
                "cities": {
                    "sao paulo": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},
                    "rio de janeiro": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            }
        }
    },
    "oceania": {
        "countries": {
            "australia": {
                "inflation": 3.8,
                "cost_of_living_index": 68,
                "currency": "AUD",
                "cities": {
                    "sydney": {"inflation_adjustment": 1.2, "cost_of_living_adjustment": 1.3},
                    "melbourne": {"inflation_adjustment": 1.1, "cost_of_living_adjustment": 1.2}
                }
            }
        }
    }
}

# Exchange rates (relative to USD, mock values for June 2025)
exchange_rates = {
    "USD": 1.0,
    "EUR": 0.93,
    "GBP": 0.78,
    "CAD": 1.38,
    "AUD": 1.50,
    "JPY": 150.0,
    "INR": 85.0,
    "BRL": 5.60,
    "ZAR": 18.0,
    "NGN": 1600.0
}

# Currency symbols for display
currency_symbols = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "JPY": "¥",
    "INR": "₹",
    "BRL": "R$",
    "ZAR": "R",
    "NGN": "₦"
}

# Minimum recommended percentages of income for each Maslow level
maslow_minimums = {
    "physiological": 0.40,  # 40% of income for food, shelter, etc.
    "safety": 0.20,        # 20% for safety (e.g., insurance, savings)
    "social": 0.10,        # 10% for social activities
    "esteem": 0.05,        # 5% for esteem (e.g., education)
    "self_actualization": 0.05  # 5% for self-actualization
}

# Endpoint to get list of continents
@app.route('/api/continents', methods=['GET'])
def get_continents():
    continents = [{"name": continent.capitalize()} for continent in economic_data.keys()]
    continents.sort(key=lambda x: x["name"])
    return jsonify(continents)

# Endpoint to get list of countries for a continent
@app.route('/api/countries/<continent>', methods=['GET'])
def get_countries(continent):
    continent = continent.lower()
    if continent not in economic_data:
        return jsonify({"error": "Continent not found"}), 404
    countries = [
        {"name": country.capitalize(), "currency": data["currency"]}
        for country, data in economic_data[continent]["countries"].items()
    ]
    countries.sort(key=lambda x: x["name"])
    return jsonify(countries)

# Endpoint to get list of cities for a country
@app.route('/api/cities/<continent>/<country>', methods=['GET'])
def get_cities(continent, country):
    continent = continent.lower()
    country = country.lower()
    if continent not in economic_data or country not in economic_data[continent]["countries"]:
        return jsonify({"error": "Country or continent not found"}), 404
    cities = [
        {"name": city.capitalize()}
        for city in economic_data[continent]["countries"][country]["cities"].keys()
    ]
    cities.sort(key=lambda x: x["name"])
    return jsonify(cities)

@app.route('/api/budget', methods=['POST'])
def calculate_budget():
    data = request.get_json()
    email = data.get('email')
    income = float(data.get('income'))  # Income in user's currency
    expenses = float(data.get('expenses'))  # Expenses in user's currency
    savings_goal = float(data.get('savings_goal'))  # Savings goal in user's currency
    continent = data.get('continent', '').lower()
    country = data.get('country', '').lower()
    city = data.get('city', '').lower()
    currency = data.get('currency', 'USD')
    expense_categories = data.get('expense_categories', {})

    # Extract categorized expenses
    physiological = expense_categories.get('physiological', 0)
    safety = expense_categories.get('safety', 0)
    social = expense_categories.get('social', 0)
    esteem = expense_categories.get('esteem', 0)
    self_actualization = expense_categories.get('self_actualization', 0)

    # Get economic data for the country
    if continent not in economic_data or country not in economic_data[continent]["countries"]:
        return jsonify({"error": "Country or continent not found"}), 404
    country_data = economic_data[continent]["countries"][country]
    inflation = country_data["inflation"]
    cost_of_living_index = country_data["cost_of_living_index"]

    # Adjust for city if selected
    if city and city in country_data["cities"]:
        city_data = country_data["cities"][city]
        inflation *= city_data["inflation_adjustment"]
        cost_of_living_index *= city_data["cost_of_living_adjustment"]

    # Convert amounts to USD for internal calculations
    user_currency = currency.upper()
    exchange_rate_to_usd = exchange_rates.get(user_currency, 1.0)
    income_usd = income / exchange_rate_to_usd
    expenses_usd = expenses / exchange_rate_to_usd
    savings_goal_usd = savings_goal / exchange_rate_to_usd
    physiological_usd = physiological / exchange_rate_to_usd
    safety_usd = safety / exchange_rate_to_usd
    social_usd = social / exchange_rate_to_usd
    esteem_usd = esteem / exchange_rate_to_usd
    self_actualization_usd = self_actualization / exchange_rate_to_usd

    # Calculate savings in USD
    savings_usd = income_usd - expenses_usd

    # Adjust recommended savings based on inflation
    recommended_savings_usd = savings_goal_usd * (1 + inflation / 100)

    # Adjust expenses based on cost of living
    expense_ratio = cost_of_living_index / 50
    adjusted_expenses_usd = expenses_usd * expense_ratio
    adjusted_savings_usd = income_usd - adjusted_expenses_usd

    # Convert back to user's currency for display
    savings = savings_usd * exchange_rate_to_usd
    adjusted_savings = adjusted_savings_usd * exchange_rate_to_usd
    recommended_savings = recommended_savings_usd * exchange_rate_to_usd
    physiological = physiological_usd * exchange_rate_to_usd
    safety = safety_usd * exchange_rate_to_usd
    social = social_usd * exchange_rate_to_usd
    esteem = esteem_usd * exchange_rate_to_usd
    self_actualization = self_actualization_usd * exchange_rate_to_usd
    min_physiological = maslow_minimums["physiological"] * income
    min_safety = maslow_minimums["safety"] * income
    min_social = maslow_minimums["social"] * income
    min_esteem = maslow_minimums["esteem"] * income
    min_self_actualization = maslow_minimums["self_actualization"] * income

    # Generate a message based on savings
    if savings >= savings_goal:
        message = "Great job! You're meeting your savings goal."
    else:
        message = "You need to save more to meet your goal. Consider reducing expenses."

    # Check Maslow's Hierarchy of Needs
    recommendations = []
    # Physiological needs
    if physiological < min_physiological:
        recommendations.append(f"Your physiological expenses ({currency_symbols[user_currency]}{physiological:.2f}) are below the recommended minimum ({currency_symbols[user_currency]}{min_physiological:.2f}). Reallocate funds from higher-level needs (e.g., social, self-actualization) to cover basic needs like food and shelter.")
    # Safety needs (only check if physiological needs are met)
    if physiological >= min_physiological:
        if safety < min_safety:
            recommendations.append(f"Your safety expenses ({currency_symbols[user_currency]}{safety:.2f}) are below the recommended minimum ({currency_symbols[user_currency]}{min_safety:.2f}). Ensure you allocate enough for insurance, emergency savings, or financial security.")
    # Higher-level needs (only recommend if lower needs are met)
    if physiological >= min_physiological and safety >= min_safety:
        if social < min_social:
            recommendations.append(f"Your social expenses ({currency_symbols[user_currency]}{social:.2f}) are below the recommended minimum ({currency_symbols[user_currency]}{min_social:.2f}). Consider allocating more for social activities to improve your relationships and well-being.")
        if esteem < min_esteem:
            recommendations.append(f"Your esteem expenses ({currency_symbols[user_currency]}{esteem:.2f}) are below the recommended minimum ({currency_symbols[user_currency]}{min_esteem:.2f}). Allocate some funds for education or personal achievements.")
        if self_actualization > 0 and (physiological < min_physiological or safety < min_safety):
            recommendations.append(f"You’re spending {currency_symbols[user_currency]}{self_actualization:.2f} on self-actualization (e.g., hobbies), but your basic needs aren’t fully met. Reallocate these funds to physiological or safety needs.")

    # Other recommendations
    if expenses > 0.7 * income:
        recommendations.append("Your expenses are high. Try cutting down on non-essential spending.")
    if savings < 0:
        recommendations.append("You're spending more than you earn. Create a stricter budget.")
    if cost_of_living_index > 60:
        location_name = city.capitalize() if city else country.capitalize()
        recommendations.append(f"Living in {location_name} is expensive. Consider finding cheaper alternatives for housing and daily expenses.")
    elif cost_of_living_index < 45:
        location_name = city.capitalize() if city else country.capitalize()
        recommendations.append(f"Living in {location_name} is relatively affordable. You can allocate more towards savings or investments.")
    recommendations.append("Consider investing in low-risk options like bonds or savings accounts.")

    # Store the budget entry in history (store in user's currency)
    budget_entry = {
        'id': len(budget_history) + 1,
        'email': email,
        'income': income,
        'expenses': expenses,
        'savings': savings,
        'savings_goal': savings_goal,
        'recommended_savings': recommended_savings,
        'message': message,
        'currency': user_currency,
        'timestamp': datetime.utcnow().isoformat()
    }
    budget_history.append(budget_entry)

    return jsonify({
        'savings': savings,
        'adjusted_savings': adjusted_savings,
        'recommended_savings': recommended_savings,
        'inflation': inflation,
        'cost_of_living_index': cost_of_living_index,
        'message': message,
        'currency': user_currency,
        'currency_symbol': currency_symbols[user_currency],
        'recommendations': recommendations,
        'expense_categories': {
            'physiological': physiological,
            'safety': safety,
            'social': social,
            'esteem': esteem,
            'self_actualization': self_actualization
        }
    })

@app.route('/api/budget/history', methods=['POST'])
def get_budget_history():
    data = request.get_json()
    email = data.get('email')
    user_history = [entry for entry in budget_history if entry['email'] == email]
    return jsonify(user_history)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

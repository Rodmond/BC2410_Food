import requests
import pandas as pd
from tkinter import messagebox, Label, Entry, Button, Scale, Tk, Toplevel, StringVar, OptionMenu
import tkinter as tk
from tkinter.ttk import Treeview
from tkinter import Y, END, W, E, N, S
from json import dumps
import tkinter.font as tkFont
from gurobipy import Model, GRB, quicksum
import pandas as pd

# Create a list to store the dishes and their interest levels
dishes = []
nutrition_data = pd.DataFrame()
rec_calories = []

# Define the activity factors
activity_factors = {
    'sedentary': 1.2,
    'lightly active': 1.375,
    'moderately active': 1.55,
    'very active': 1.725,
    'extra active': 1.9
}

nl = '\n'

#from sklearn.metrics.pairwise import cosine_similarity

def diet_planner(df, calorie_upper, calorie_lower):
    # Create a new model
    m = Model("diet_planner")

     # Add decision variables
    food_vars = m.addVars(df.index, vtype=GRB.CONTINUOUS, name="food")
    food_chosen = m.addVars(df.index, vtype=GRB.BINARY, name="chosen")

    # Set the objective
    m.setObjective(quicksum(food_chosen[i]*df.loc[i, 'interest_level'] for i in df.index), GRB.MAXIMIZE)

    # Add calorie constraints
    total_calories = quicksum(food_vars[i]*df.loc[i, 'calories'] for i in df.index)
    m.addConstr(total_calories <= calorie_upper, "Calorie_upper")
    m.addConstr(total_calories >= calorie_lower, "Calorie_lower")

    # Add constraint for unique food items and only 1 serving of each food portion
    m.addConstr(quicksum(food_chosen[i] for i in df.index) <= 10, "Unique_food_items")
    m.addConstr(quicksum(food_chosen[i] for i in df.index) >=3, "Unique_food_items_2")

    # Add nutrient constraints
    total_carbs = quicksum(food_vars[i]*df.loc[i, 'carbohydrates_total_g'] for i in df.index)
    total_sodium = quicksum(food_vars[i]*df.loc[i, 'sodium_mg'] for i in df.index)
    total_cholesterol = quicksum(food_vars[i]*df.loc[i, 'cholesterol_mg'] for i in df.index)
    total_fat = quicksum(food_vars[i]*df.loc[i, 'fat_total_g'] for i in df.index)
    total_fiber = quicksum(food_vars[i]*df.loc[i, 'fiber_g'] for i in df.index)
    total_saturated_fat = quicksum(food_vars[i]*df.loc[i, 'fat_saturated_g'] for i in df.index)
    
    m.addConstr(total_carbs >= 0.45 * total_calories/4, "Carbs_lower") #4 is the conversion rate from grams to kcal for carbs
    m.addConstr(total_carbs <= 0.65 * total_calories/4, "Carbs_upper")
    m.addConstr(total_sodium <= 2000, "Sodium_upper")
    m.addConstr(total_cholesterol <= 300, "Cholesterol_upper")
    m.addConstr(total_fat >= 0.20 * total_calories/9, "Fat_lower") #similarly, 9 is conversion rate for total fats
    m.addConstr(total_fat <= 0.30 * total_calories/9, "Fat_upper")
    m.addConstr(total_saturated_fat<=22, "saturated_fat_upper")
    m.addConstr(total_fiber >=25, "Fiber_lower")
    m.addConstr(total_fiber <= 38 , "Fiber_Upper")

    # Link food_vars and food_chosen
    for i in df.index:
        if df.loc[i, 'calories'] < 250: #edit here if needed
            m.addConstr(food_vars[i] <= 2 * food_chosen[i])
        else:
            m.addConstr(food_vars[i] <= 1.5 * food_chosen[i])
        m.addConstr(food_vars[i] >= 0.5 * food_chosen[i])

    # Solve the model
    m.setParam('OutputFlag', 0)
    m.optimize()

    # Check the status of the model
    if m.status == GRB.Status.OPTIMAL:
        messagebox.showinfo("Information",f"""
        Congratulations! We were able to create an optimal meal plan for you. The optimal diet plan is: \n
        {f'{nl}'.join([f"{df.loc[int(v.varName.split('[')[1].split(']')[0]), 'name']}: {round(v.x,1)} servings, {round(v.x * df.loc[int(v.varName.split('[')[1].split(']')[0]), 'calories'],1)} calories" for v in m.getVars() if v.x > 0 and 'chosen' not in v.varName])}
        \n
        
        Total calories: {total_calories.getValue()} kCal \n
        Total carbohydrates: {total_carbs.getValue()} grams \n
        Total sodium: {total_sodium.getValue()} miligrams \n
        Total cholesterol: {total_cholesterol.getValue()} miligrams \n
        Total fat: {total_fat.getValue()} grams \n
        Total fiber: {total_fiber.getValue()} grams \n
        Total saturated fat: {total_saturated_fat.getValue()} grams \n
        """)
    else: #recommend new plan
        messagebox.showinfo("Infomation",f"""Unfortunately, we were unable to come up with a suitable meal plan to meet your needs. \n
              It is likely that you were lacking in certain important food categories in your diet. \n
              Here are some general foods that we recommend to include in your diet: \n 
              Salads like Caesar Salads, Garden Salads \n
              Fruits like Apples, Bananas, \n
              Vegetables like Eggplant, Broccoli, Carrots \n
              Sandwiches like Chicken Sandwiches, Vegetable Sandwiches \n

              In addition, you could consider adding food options that you like that have: \n
              Low Sodium Foods such as Salmon, Tofu \n
              Grain with no added salt such as Cereals \n
              Proteins such as Eggs and fresh fish \n
              Carbohydrates such as Brown Rice, Berries, Sweet Potatoes

              Please add in some additional food options and try again :)
              """) #future improvement recommendation system
        return

healthier_foods = []

class Tooltip:
    def __init__(self, widget, text):
        self.waittime = 500     # milliseconds before tooltip shows
        self.wraplength = 180   # pixels before text wraps
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # Creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

def calculate_caloric_intake(weight, height_m, age, activity_factor, gender):
    height_cm = height_m * 100
    BMI = weight / (height_m) ** 2
    
    if BMI > 25:
        if gender == "male":
            LBM = 0.407 * weight + 0.267 * height_cm - 19.2
        else:
            LBM = 0.252 * weight + 0.473 * height_cm - 48.3

        BMR = 370 + 21.6 * LBM
        calories = BMR * activity_factor
        rec_calories = (calories - 400, calories)
        return rec_calories
    else:
        return None
    
def handle_caloric_intake():
    global rec_calories
    weight = float(weight_entry.get())
    height_m = float(height_entry.get()) / 100  # Convert cm to m for calculation
    age = int(age_entry.get())  # Assuming you add an Entry for age
    gender = gender_var.get()
    activity_level = activity_var.get()
    
    rec_calories = calculate_caloric_intake(weight, height_m, age, activity_factors[activity_level], gender)
    
    if rec_calories:
        messagebox.showinfo("Caloric Intake", f"Recommended calorie intake is: {rec_calories}")
    else:
        messagebox.showinfo("Caloric Intake", "You do not need to lose weight")
    return rec_calories

def show_help():
    messagebox.showinfo("Help", "This application allows you to track the nutrition of dishes. \n\n"
                       "1. Enter a dish name and press 'Get Nutrition Data' to add it to your list.\n"
                       "2. Use the scale to indicate your interest level in each dish.\n"
                       "3. The 'Total Nutrients' button shows a summary of all added dishes.\n"
                       "4. You can reset at any time with the 'Reset Data' button.\n\n"
                       "Make sure to add a variety of dishes including fruits and vegetables for a balanced diet.")


def reset_data():
    global dishes, nutrition_data
    dishes = []
    nutrition_data = pd.DataFrame()
    update_treeview()

def fetch_nutrition_data(dish):
    api_url = 'https://api.api-ninjas.com/v1/nutrition?query={}'
    headers = {'X-Api-Key': 'YfTAXnJRO26E9bKhFRXXSg==4ZfGRF5zrSIl3CNY'}
    one_portion_dish = f"1 {dish}"
    response = requests.get(api_url.format(one_portion_dish), headers=headers)
    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        messagebox.showerror("Error", f"Error: {response.status_code} {response.text}")
        return None
    
def handle_dish_input(dish, interest_level):
    # Remove the old data if dish already exists
    global dishes, nutrition_data
    if any(d for d, _ in dishes if d == dish):
        messagebox.showinfo("Info", "This dish has already been added. It will replace the previous one.")
        dishes = [(d, i) for d, i in dishes if d != dish]
        nutrition_data = nutrition_data[nutrition_data['food'] != dish]

    # Add the dish and its interest level to the list
    dishes.append((dish, interest_level))

    # Fetch nutrition data and update the DataFrame
    nutrition_json = fetch_nutrition_data(dish)
    if nutrition_json:
        df = pd.DataFrame(nutrition_json, index=[0])
        df['interest_level'] = interest_level
        nutrition_data = pd.concat([nutrition_data, df], ignore_index=True)


def get_nutrition():
    dish = dish_name.get().lower().strip()
    interest_level = interest_scale.get()

    # Handle the dish input and update UI
    handle_dish_input(dish, interest_level)

    # Update the Treeview widget
    update_treeview()

def update_treeview():
    # Clear the Treeview widget
    for i in tree.get_children():
        tree.delete(i)
    # Insert the data into the Treeview widget
    for index, row in nutrition_data.iterrows():
        tree.insert('', 'end', values=list(row))

# def validate_diet_planner():
#     if (sum(d in fruits for d, _ in dishes) < 1 or sum(d in vegetables for d, _ in dishes) < 1):
#         messagebox.showinfo("Info", "You must select a fruit or vegetable in your foods of choice. Please add some of them in.")
#         return
#     else:
#         display_total_nutrients()
    

def display_total_nutrients():
    if rec_calories==[]:
        messagebox.showinfo("Info","Please key in your personal information first.")
        return
    else:
        #Optimisation Plan will be inserted here
        calories_lower = rec_calories[0]
        calories_upper = rec_calories[1]

        diet_planner(nutrition_data,calories_upper,calories_lower)

        # # Calculate the total nutrients consumed
        # total_nutrients = nutrition_data.sum(numeric_only=True)

        # # Calculate the average interest level
        # avg_interest_level = nutrition_data['interest_level'].mean()

        # # Replace the total interest level with the average interest level
        # total_nutrients['interest_level'] = avg_interest_level

        # # Display the total nutrients consumed
        # messagebox.showinfo("Total Nutrients", "Here are the total nutrients consumed:\n" + '\n'.join(f"{nutrient}: {amount}" for nutrient, amount in total_nutrients.items()))

# Create a Tkinter window
window = Tk()
window.title("Nutrition Data")
window.geometry("800x600")
window.resizable(True, True)
window.grid_columnconfigure(0, weight=1)
window.grid_rowconfigure(0, weight=1)

# Define a custom font
# heading_font = tkFont.Font(family='Helvetica', size=18, weight='bold') font=heading_font
instruction_font = tkFont.Font(family='Helvetica', size=10, slant='italic')

# Add a heading Label
heading_label = Label(window, text="Welcome to the Nutrition Tracker")
heading_label.grid(row=0, column=0, columnspan=3, sticky=W+E, pady=10)

# Add instructional text below the heading
instruction_text = "Fill in the dish's name and your interest level, then click 'Input' to add it to the list."
instruction_label = Label(window, text=instruction_text, font=instruction_font)
instruction_label.grid(row=1, column=0, columnspan=3, sticky=W, padx=10)

# Create a Label for the Entry field
dish_label = Label(window, text="Enter the name of the dish:")
dish_label.grid(row=2, column=0, sticky=W)

# Create an Entry field for the dish name
dish_name = Entry(window, width=50)
dish_name.grid(row=3, column=0, sticky=W+E)

# Create a Label for the Scale widget
interest_label = Label(window, text="Indicate your interest in the dish:")
interest_label.grid(row=4, column=0, sticky=W)

# Create a Scale widget for the interest level
interest_scale = Scale(window, from_=1, to=10, orient="horizontal")
interest_scale.grid(row=5, column=0, sticky=W+E)

# Create a Button that will call the get_nutrition function when clicked
get_button = Button(window, text="Enter", command=get_nutrition)
get_button.grid(row=6, column=0, sticky=W+E)

# Create a Button that will display the total nutrients when clicked
total_button = Button(window, text="Total Nutrients", command=display_total_nutrients)
total_button.grid(row=7, column=0, sticky=W+E)

# Create a Button that will reset the data when clicked
reset_button = Button(window, text="Reset Data", command=reset_data)
reset_button.grid(row=8, column=0, sticky=W+E)

help_button = Button(window, text="Help", command=show_help)
help_button.grid(row=9, column=0, sticky=W+E)

# Create frames for better organization
input_frame = tk.Frame(window)
input_frame.grid(row=10, column=0, sticky=W+E+N+S, padx=5, pady=5)

tk.Label(input_frame, text="Weight (kg):").grid(row=0, column=0, sticky=W, padx=5, pady=5)
weight_entry = tk.Entry(input_frame)
weight_entry.grid(row=0, column=1, sticky=E, padx=5, pady=5)

tk.Label(input_frame, text="Height (cm):").grid(row=1, column=0, sticky=W, padx=5, pady=5)
height_entry = tk.Entry(input_frame)
height_entry.grid(row=1, column=1, sticky=E, padx=5, pady=5)

tk.Label(input_frame, text="Age (years):").grid(row=2, column=0, sticky=W, padx=5, pady=5)
age_entry = tk.Entry(input_frame)
age_entry.grid(row=2, column=1, sticky=E, padx=5, pady=5)

# Create option menu for activity level
activity_var = StringVar(window)
activity_var.set("sedentary")  # default value

# Create option menu for gender
gender_var = StringVar(window)
gender_var.set("male")  # default value

# Use a frame for the radio buttons or option menus
options_frame = tk.Frame(window)
options_frame.grid(row=11, column=0, sticky=W+E+N+S, padx=5, pady=5)

# Add option menu for activity level
activity_var = tk.StringVar(window)
activity_var.set('sedentary')  # set default value
tk.Label(options_frame, text="Activity Level:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
activity_factor_menu = tk.OptionMenu(options_frame, activity_var, *activity_factors.keys())
activity_factor_menu.grid(row=0, column=1, sticky=E, padx=5, pady=5)

# Add option menu for gender
gender_var = tk.StringVar(window)
gender_var.set("male")  # set default value
tk.Label(options_frame, text="Gender:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
gender_menu = tk.OptionMenu(options_frame, gender_var, "male", "female")
gender_menu.grid(row=1, column=1, sticky=E, padx=5, pady=5)

calculate_button = tk.Button(window, text="Calculate Caloric Intake", command=handle_caloric_intake)
calculate_button.grid(row=12, column=0, sticky=W+E, padx=10, pady=10)

tooltip_dish_name = Tooltip(dish_name, "Enter the name of the dish you're adding. For example: 'apple', 'pizza', etc.")

# For the interest level Scale widget
tooltip_interest_level = Tooltip(interest_scale, "Slide to indicate how much you are interested in this dish on a scale of 1 to 10.")


# Create a Treeview widget to display nutrition data
tree = Treeview(window)
tree["columns"] = ("", "calories", "serving_size_g", "fat_total_g", "fat_saturated_g", "protein_g", "sodium_mg", "potassium_mg", "cholesterol_mg", "carbohydrates_total_g", "fiber_g", "sugar_g", "interest_level")
tree.column("#0", width=0, minwidth=0, stretch=False)
tree.heading("#0", text="")
tree.heading("calories", text="Calories", anchor="center")
tree.heading("serving_size_g", text="Serving Size (g)", anchor="center")
tree.heading("fat_total_g", text="Total Fat (g)", anchor="center")
tree.heading("fat_saturated_g", text="Saturated Fat (g)", anchor="center")
tree.heading("protein_g", text="Protein (g)", anchor="center")
tree.heading("sodium_mg", text="Sodium (mg)", anchor="center")
tree.heading("potassium_mg", text="Potassium (mg)", anchor="center")
tree.heading("cholesterol_mg", text="Cholesterol (mg)", anchor="center")
tree.heading("carbohydrates_total_g", text="Total Carbohydrates (g)", anchor="center")
tree.heading("fiber_g", text="Fiber (g)", anchor="center")
tree.heading("sugar_g", text="Sugar (g)", anchor="center")
tree.heading("interest_level", text="Interest Level", anchor="center")
tree.grid(row=13, column=0, sticky=W+E+N+S)

# Run the Tkinter event loop
window.mainloop()
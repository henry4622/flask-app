from flask import Flask, flash, redirect, render_template, request, session, make_response, url_for
from flask_session import Session
import sqlite3
from validate_email_address import validate_email
import hashlib
import requests
import datetime
import smtplib
from email.message import EmailMessage






app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' 
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

if __name__ == "__main__":
    app.run(debug=True)


db = sqlite3.connect('database.db', check_same_thread=False)


def close_db(db):
    db.commit() 
    db.close()


def run_query(query, params=()):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result



@app.route('/')
def home():
    name = request.cookies.get('firstname')
    return render_template("home.html",name=name)
        

@app.route('/login', methods=['POST', 'GET'])
def login():
    email_error = False
    password_error = False

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        actual_email = run_query("SELECT email FROM users WHERE email = ?", (email,))
        actual_password = run_query("SELECT hash FROM users WHERE email = ?", (email,))

        if actual_email is None:
            email_error = True
        elif actual_email and actual_password:
            stored_hash = actual_password[0]

        if stored_hash != hashlib.sha256(password.encode('utf-8')).hexdigest():
            password_error = True

        else:

            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('email', email, httponly=True)
            resp.set_cookie('firstname', actual_email[0]['firstname'], httponly=True)
            
            return resp
        
        return render_template("login.html", email_error=email_error, password_error=password_error)
            

    else:
        return render_template("login.html")


@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie("email", "", expires=0)
    resp.set_cookie("firstname", "", expires=0)
    resp.set_cookie("surname", "", expires=0)
    resp.set_cookie("password", "", expires=0)
    resp.set_cookie("date_of_birth", "", expires=0)
    resp.set_cookie("date", "", expires=0)
    resp.set_cookie("shipping_service", "", expires=0)
    resp.set_cookie("postcode", "", expires=0)
    resp.set_cookie("address", "", expires=0)
    resp.set_cookie("town", "", expires=0)
    resp.set_cookie("county", "", expires=0)
    resp.set_cookie("email", "", httponly=True)


    return resp

    
@app.route('/register', methods=['POST', 'GET'])
def register():
    password_error = False
    birth_error = False
    surname_error = False
    firstname_error = False
    email_error = False
    email_error2 = False

    if request.method == "POST":
        firstname = request.form.get("firstname")
        surname = request.form.get("surname")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        month = request.form.get("month").zfill(2)
        day = request.form.get("day").zfill(2)
        year = request.form.get("year")
        email = request.form.get("email")

        date_of_birth = day + month + year
        print(date_of_birth)
        print(f"Firstname: '{firstname}', Surname: '{surname}'")

        if password != password2 and password and password2:
            password_error = True

        if not (day.isdigit() and month.isdigit() and year.isdigit()):
            birth_error = True
        else:
            day, month, year = int(day), int(month), int(year)
            if day > 31 or day < 1 or month > 12 or month < 1 or year > 2025 or year < 1900:
                birth_error = True

        if not firstname or not firstname.isalpha():
            firstname_error = True

        if not surname or not surname.isalpha():
            surname_error = True

        if not validate_email(email):
            email_error = True
        else:
            emails = run_query("SELECT * FROM users WHERE email = ?", (email,))
            if emails:
                email_error2 = True

        if not (email_error or surname_error or firstname_error or birth_error or password_error or email_error2):
            hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            run_query("INSERT INTO users (firstname, surname, hash, date_of_birth, email) VALUES (?, ?, ?, ?, ?)", 
                           (firstname, surname, hash, date_of_birth, email))
            print("User added successfully:", firstname, surname, email)

            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('email', email, httponly=True)
            resp.set_cookie('firstname', firstname, httponly=True)
            return resp

        return render_template("register.html", password_error=password_error, birth_error=birth_error, 
                               firstname_error=firstname_error, surname_error=surname_error, 
                               email_error=email_error, email_error2=email_error2)

    return render_template("register.html", password_error=False, birth_error=False, firstname_error=False, 
                           surname_error=False, email_error=False, email_error2=False)

@app.route('/prebuilds', methods=['POST', 'GET'])
def prebuilds():
    name = request.cookies.get('firstname')
    pcs = run_query("SELECT * FROM products")
    return render_template("prebuilds.html", name=name, pcs=pcs)


@app.route('/add_to_basket', methods= ['POST', 'GET'])
def add_to_basket():
    
    if request.method == "POST":
        product_name = request.form.get("prebuild")
        prebuild_info = run_query("SELECT * FROM products WHERE name = ?", (product_name,))
        print(prebuild_info)
        email = request.cookies.get('email')

        if not email:
            return redirect(url_for('login'))

        price = run_query("SELECT price FROM products WHERE name = ?", (product_name,))
        if not price:
            return "Product not found", 404
        existing_product = run_query("SELECT * FROM basket WHERE user_email = ? AND name = ?", (email, product_name))
        if existing_product:
            run_query("UPDATE basket SET quantity = quantity + 1 WHERE user_email = ? AND name = ?", (email, product_name))
        else:
            run_query("INSERT INTO basket (user_email, name, price, type, cpu, motherboard, ram, gpu, storage, cooler, psu, pc_case) VALUES (?, ?, ?,?,?,?,?,?,?,?,?,?)", (email, product_name, price[0]['price'], "Prebuild", prebuild_info[0]['cpu'], prebuild_info[0]['motherboard'], prebuild_info[0]['ram'], prebuild_info[0]['gpu'], prebuild_info[0]['storage'], prebuild_info[0]['cooling'], prebuild_info[0]['psu'], prebuild_info[0]['pc_case']))


    return '',204
            
@app.route('/basket', methods= ['GET'])
def basket():
    email = request.cookies.get('email')
    products = run_query("SELECT * FROM basket WHERE user_email = ?", (email,))
    total_price = round(sum(product['price'] * product['quantity'] for product in products),2)
    first_name = request.cookies.get("firstname")
    predbuilds = run_query("SELECT * FROM products")
    customs = run_query("SELECT * FROM custom_builds WHERE email = ?", (email,))
    names =  run_query("SELECT name FROM basket WHERE user_email = ?", (email,))
    names = [name['name'] for name in names]  
    return render_template("basket.html", products=products, total_price=total_price, firstname=first_name, customs=customs, predbuilds=predbuilds, names=names,)




@app.route('/compare', methods=['GET','POST'])
def compare():
    pcs = run_query("SELECT * FROM products") 
    name = request.cookies.get('firstname')

    if 'selected_pcs' not in session:
        session['selected_pcs'] = []

    selected_ids = session['selected_pcs']

    if request.method == 'POST':
        for pc in pcs:
            pc_id = str(pc['id'])
            if request.form.get(f"show{pc_id}") == "show":
                if pc['id'] not in selected_ids:
                    selected_ids.append(pc['id'])
            elif request.form.get(f"hide{pc_id}") == "hide":
                if pc['id'] in selected_ids:
                    selected_ids.remove(pc['id'])

        session['selected_pcs'] = selected_ids

    selected_pcs = []
    for pc_id in selected_ids:
        result = run_query("SELECT * FROM products WHERE id = ?", (pc_id,))
        if result:
            selected_pcs.append(result[0])  

    return render_template("compare.html", pcs=pcs, selected_pcs=selected_pcs, name=name)



@app.route('/filter_pcs', methods=['POST'])
def filter_pcs():
    pcs = run_query("SELECT * FROM products")
    cpuFilter = request.form.get('cpuFilter', '').lower()
    gpuFilter = request.form.get('gpuFilter', '').lower()
    ramFilter = request.form.get('ramFilter', '').lower()
    storageFilter = request.form.get('storageFilter', '').lower()
    priceFilter = request.form.get('priceFilter', '').lower()
    categoryFilter = request.form.get('categoryFilter', '').lower()
    name = request.cookies.get('firstname')
    filtered_pcs = pcs
    filtered = False
        
    if cpuFilter and cpuFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if cpuFilter in pc['cpu'].lower()]

    if ramFilter and ramFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if ramFilter in pc['ram'].lower()]

    if gpuFilter and gpuFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if gpuFilter in pc['gpu'].lower()]

    if storageFilter and storageFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if storageFilter in pc['storage'].lower()]

    if priceFilter and priceFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if priceFilter in pc['price_range'].lower()]
    
    if categoryFilter and categoryFilter != "all":
        filtered_pcs = [pc for pc in filtered_pcs if categoryFilter in pc['use'].lower()]

    if filtered_pcs == []:
        error = "No items found"
        return render_template("prebuilds.html", pcs=pcs, error=error, name=name) 
    else:
        filtered = True
   
    return render_template("prebuilds.html", pcs=filtered_pcs, cpuFilter=cpuFilter, gpuFilter=gpuFilter, ramFilter=ramFilter, storageFilter=storageFilter, priceFilter=priceFilter, categoryFilter=categoryFilter, filtered=filtered, name=name)
        
@app.route('/reccomendations', methods=['POST','GET'])
def reccomendations():
    name = request.cookies.get('firstname')

    if request.method == 'POST':
        pcs = run_query("SELECT * FROM products")
        cpu = request.form.get('cpu', '').lower()
        gpu = request.form.get('gpu', '').lower()
        storage = request.form.get('storage', '').lower()
        price = request.form.get('price', '').lower()
        use = request.form.get('use', '').lower()
        case = request.form.get('case', '').lower()
        filtered_pcs = pcs
        applied = False

        if cpu and gpu and storage and price and use and case:
            applied = True

            if cpu and cpu != "all":
                filered_pcs = [pc for pc in filtered_pcs if cpu in pc['cpu'].lower()]
            elif cpu and cpu == "all":
                filtered_pcs = filtered_pcs

            if gpu and gpu != "all":
                filtered_pcs = [pc for pc in filtered_pcs if gpu in pc['gpu'].lower()]
            elif gpu and gpu == "all":
                filtered_pcs = filtered_pcs

            if storage and storage != "all":
                filtered_pcs = [pc for pc in filtered_pcs if storage in pc['storage_amount'].lower()]
            elif storage and storage == "all":
                filtered_pcs = filtered_pcs

            if price:
                filtered_pcs = [pc for pc in filtered_pcs if price in pc['price_range'].lower()]


            if use and use != "all":
                filtered_pcs = [pc for pc in filtered_pcs if use in pc['use'].lower()]


            if case and case != "all":
                filtered_pcs = [pc for pc in filtered_pcs if case in pc['case_style'].lower()]
            elif case and case == "all":
                filtered_pcs = filtered_pcs

            if filtered_pcs == []:
                error = "No items matched your search please try adjusting some of the filters"
                return render_template("reccomendations.html", error=error, applied=applied, name=name)
        else:
            error = "Please fill in all the fields"
            return render_template("reccomendations.html", pcs=pcs, error=error, applied=applied, name=name)
        
        return render_template("reccomendations.html", applied=applied, pcs=filtered_pcs, cpu=cpu, gpu=gpu, storage=storage, price=price, use=use, case=case, name=name )
    else:
        return render_template("reccomendations.html", name=name)
    

@app.route('/what_to_look_for', methods=['GET'])
def what_to_look_for():
    return render_template("lookfor.html")

@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    name = request.cookies.get('firstname')
    if request.method == 'POST':

        postcode = request.form.get('postcode')
        print(is_valid_postcode(postcode))
        print(is_eligible_postcode(postcode, allowed_counties))

        if is_valid_postcode(postcode):

            if is_eligible_postcode(postcode, allowed_counties):
                return render_template("delivery.html", valid_postcode=True, postcode=postcode, valid_county=True, name=name)
            
            else:
                return render_template("delivery.html", valid_postcode=True, postcode=postcode, valid_county=False, name=name)
            
        else:
            return render_template("delivery.html", valid_postcode=False, postcode=postcode, valid_county=False , name=name)
    
    else:
        return render_template("delivery.html", name=name)

allowed_counties = ["Bedfordshire", "Berkshire", "Bristol", "Buckinghamshire", "Cambridgeshire", "Cheshire", "City of London", "Cornwall", "Cumbria", "Derbyshire", "Devon", "Dorset", "Durham", "East Riding of Yorkshire", "East Sussex", "Essex", "Gloucestershire", "Greater London", "Greater Manchester", "Hampshire", "Herefordshire", "Hertfordshire", "Kent", "Lancashire", "Leicestershire", "Lincolnshire", "Merseyside", "Norfolk", "North Yorkshire", "Northamptonshire", "Northumberland", "Nottinghamshire", "Oxfordshire", "Rutland", "Shropshire", "Somerset", "South Yorkshire", "Staffordshire", "Suffolk", "Surrey", "Tyne and Wear", "Warwickshire", "West Midlands", "West Sussex", "West Yorkshire", "Wiltshire", "Worcestershire"]

def is_eligible_postcode(postcode, allowed_counties):
    postcode = postcode.replace(" ", "")
    url = f"https://api.postcodes.io/postcodes/{postcode}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200 or data['status'] != 200:
        return False    

    district = data['result']['admin_district']
    return district in allowed_counties

def is_valid_postcode(postcode):
    postcode = postcode.replace(" ", "")  # Remove spaces
    url = f"https://api.postcodes.io/postcodes/{postcode}/validate"
    response = requests.get(url)
    data = response.json()
    return data['result']

@app.route('/prebuild_info', methods=['GET'])
def prebuild_info():
    firstname = request.cookies.get('firstname')
    return render_template("prebuild_info.html", name=firstname)

@app.route('/user', methods=['GET', 'POST'])
def user():
    user = request.cookies.get('firstname')
    return render_template("user.html",user=user)

@app.route('/checkout-shipping', methods=['GET', 'POST'])
def checkout_shipping():
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    if request.method == 'POST' and not any(request.form.values()):
        return render_template("checkout-shipping.html", date=date, error=None)
    error = None
    if request.method == 'POST':
        service = request.form.get('shipping_service')

        firstname = request.form.get('firstname')
        surname = request.form.get('surname')
        postcode = request.form.get('postcode')
        address = request.form.get('address')
        town = request.form.get('town')
        county = request.form.get('county')
        basket = run_query("SELECT * FROM basket WHERE user_email = ?", (request.cookies.get('email'),))

        if basket is None or len(basket) == 0:
            return render_template("checkout-shipping.html", date=date, error="Your basket is empty")
        if service == None:
            return render_template("checkout-shipping.html", date=date, error="Please select a shipping service")
        if not is_valid_postcode(postcode):
            return render_template("checkout-shipping.html", date=date, error="Invalid postcode")
        if not(county in allowed_counties):
            return render_template("checkout-shipping.html", date=date, error="County not eligible for delivery")
             
        if not is_eligible_postcode(postcode, allowed_counties):
            return render_template("checkout-shipping.html", date=date, error="Postcode not eligible for delivery")
        
        resp = make_response(redirect(url_for('checkout_payment')))
        resp.set_cookie('shipping_service', service, httponly=True)
        resp.set_cookie('firstname', firstname, httponly=True)
        resp.set_cookie('surname', surname, httponly=True)
        resp.set_cookie('postcode', postcode, httponly=True)
        resp.set_cookie('address', address, httponly=True)
        resp.set_cookie('town', town, httponly=True)
        resp.set_cookie('county', county, httponly=True)
        resp.set_cookie('date', date, httponly=True)
        return resp
    else:    
        return render_template("checkout-shipping.html", date=date, error=None)

@app.route('/remove_from_basket', methods=['POST'])
def remove_from_basket():
    if request.method == "POST":
        product_name = request.form.get("product_name")
        email = request.cookies.get('email')
        print(product_name)
        run_query("DELETE FROM basket WHERE user_email = ? AND name = ?", (email, product_name))

    return redirect(url_for('basket'))

@app.route('/add1_to_basket', methods=['POST'])
def add1_to_basket():
    if request.method == "POST":
        product_name = request.form.get("product_name")
        email = request.cookies.get('email')
        run_query("UPDATE basket SET quantity = quantity + 1 WHERE user_email = ? AND name = ?", (email, product_name))

    return redirect(url_for('basket'))

@app.route('/minus1_to_basket', methods=['POST'])
def minus1_to_basket():
    if request.method == "POST":
        product_name = request.form.get("product_name")
        email = request.cookies.get('email')
        quantity = run_query("SELECT quantity FROM basket WHERE user_email = ? AND name = ?", (email, product_name))
        if quantity and quantity[0]['quantity'] > 1: 
            run_query("UPDATE basket SET quantity = quantity - 1 WHERE user_email = ? AND name = ?", (email, product_name))

    return redirect(url_for('basket'))

@app.route('/checkout-payment', methods=['GET', 'POST'])
def checkout_payment():
    email = request.cookies.get('email')
    products = run_query("SELECT * FROM basket WHERE user_email = ?", ((email,)))
    total_price = sum(product['price'] * product['quantity'] for product in products)
    shipping_service = request.cookies.get('shipping_service')
    cost = 0
    if shipping_service == "standard":
        cost = 0
    elif shipping_service == "quick":
        if total_price < 1000:
            cost = 0
        else:
            cost = 8.99
    elif shipping_service == "24hr":
        cost = 19
    
    if request.method == "POST":
        firstname = request.form.get('firstname')
        surname = request.form.get('surname')
        postcode = request.form.get('postcode')
        address = request.form.get('address')
        town = request.form.get('town')
        county = request.form.get('county')
        service = request.cookies.get('shipping_service')
        date = request.cookies.get('date')  
        run_query("INSERT INTO shipping (firstname, surname, postcode, address, town, county, service, date) VALUES (?,?,?,?,?,?,?,?)",(firstname, surname, postcode, address, town, county, service, date))
        names = run_query("SELECT name FROM basket WHERE user_email = ?",(email,))
        names = [name['name'] for name in names]
        total_price = round(total_price + cost, 2)
        run_query("INSERT INTO orders (email, cost, shipping, date, items) VALUES (?,?,?,?,?)", (email, total_price, service, date, ",".join(names)))
        return render_template("home.html",message="order", name=firstname)
    return render_template("checkout-payment.html", total_price=total_price, products=products, cost=cost, shipping_service=shipping_service)

@app.route('/custom_builds', methods=['GET'])
def custom_builds():
    name = request.cookies.get('firstname')
    return render_template("custom.html", name=name)

@app.route('/design-cpu', methods=['GET','POST'])
def design_cpu():
    if request.method == 'POST':
        component_name = request.form.get("cpu")
        resp = make_response(redirect(url_for('design_motherboard')))
        resp.set_cookie("cpu", component_name, httponly=True)
        return resp
    cpus = run_query("SELECT component_name,retail_price FROM stock WHERE component_type = 'cpu' ORDER BY retail_price ASC")
    return render_template("design.html",cpus=cpus)

@app.route('/design-motherboard', methods=['GET','POST'])
def design_motherboard():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))
    cpu_soccket = run_query("SELECT socket_type FROM stock WHERE component_name = ?", (cpu,))
    motherboards = run_query("SELECT component_name, retail_price, ram_type, factor FROM stock WHERE component_type = 'motherboard' AND socket_type = ? ORDER BY retail_price ASC", (cpu_soccket[0]['socket_type'],))
    if request.method == "POST":
        motherboard = request.form.get("motherboard")
        resp = make_response(redirect(url_for('design_ram')))
        resp.set_cookie("motherboard",motherboard, httponly=True)
        return resp
    return render_template("design-motherboard.html", cpu=cpu, cpu_price=cpu_price[0]['retail_price'], motherboards=motherboards)

@app.route('/design-ram', methods=['GET','POST'])
def design_ram():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))
    ram_type = run_query("SELECT ram_type FROM stock WHERE component_name = ?", (motherboard,))
    rams = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'ram' and ram_type = (?) ORDER by retail_price ASC", (ram_type[0]['ram_type'],))
    if request.method == "POST":
        ram = request.form.get("ram")
        resp = make_response(redirect(url_for('design_gpu')))
        resp.set_cookie("ram", ram, httponly=True)
        return resp
    return render_template("design-ram.html", motherboard=motherboard, motherboard_price=int(motherboard_price[0]['retail_price']), cpu=cpu, cpu_price=int(cpu_price[0]['retail_price']), rams=rams, ram_type=ram_type)


@app.route('/design-gpu', methods=['GET','POST'])
def design_gpu():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))
    ram = request.cookies.get('ram')
    ram_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ram,))
    gpus = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'gpu' ORDER BY retail_price ASC")
    if request.method == "POST":
        gpu = request.form.get("gpu")
        resp = make_response(redirect(url_for('design_storage')))
        resp.set_cookie("gpu",gpu, httponly=True)
        return resp
    return render_template("design-gpu.html", cpu=cpu, cpu_price=int(cpu_price[0]['retail_price']), motherboard=motherboard, motherboard_price=int(motherboard_price[0]['retail_price']), ram=ram, ram_price=int(ram_price[0]['retail_price']), gpus=gpus)

@app.route('/design-psu', methods=['GET','POST'])
def design_psu():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))[0]['retail_price']
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))[0]['retail_price']
    ram = request.cookies.get('ram')
    ram_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ram,))[0]['retail_price']
    gpu = request.cookies.get('gpu')
    gpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (gpu,))[0]['retail_price']
    storage_price = request.cookies.get('storage_price')
    storage = request.cookies.get('storage').split(",")
    coolers = request.cookies.get('cooler')
    cooler_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (coolers,))[0]['retail_price']
    psus = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'psu' ORDER BY retail_price ASC")
    cpu_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (cpu,))[0]['wattage']
    motherboard_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (motherboard,))[0]['wattage']
    ram_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (ram,))[0]['wattage']
    gpu_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (gpu,))[0]['wattage']
    cooler_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (coolers,))[0]['wattage']
    total_wattage = int(cpu_wattage) + int(motherboard_wattage) + int(ram_wattage) + int(gpu_wattage) + int(cooler_wattage) + 150
    suitable_psus = []
    for psu in psus:
        psu_wattage = run_query("SELECT wattage FROM stock WHERE component_name = ?", (psu['component_name'],))
        if int(psu_wattage[0]['wattage']) >= total_wattage:
            suitable_psus.append(psu)
    if request.method == "POST":
        psu = request.form.get("psu")
        resp = make_response(redirect(url_for('design_case')))
        resp.set_cookie("psu", psu, httponly=True)
        return resp
    return render_template("design-psu.html", cpu=cpu, cpu_price=int(cpu_price), motherboard=motherboard, motherboard_price=int(motherboard_price), ram=ram, ram_price=int(ram_price), gpu=gpu, gpu_price=int(gpu_price), storage=storage, storage_price=int(storage_price), cooler=coolers, cooler_price=cooler_price, psus=suitable_psus)
    
@app.route('/design-storage', methods=['GET','POST'])    
def design_storage():
    SSDS = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'storage' AND factor = 'SSD' ORDER BY retail_price ASC")
    HDDS = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'storage' AND factor = 'HDD' ORDER BY retail_price ASC")
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))[0]['retail_price']
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))[0]['retail_price']
    ram = request.cookies.get('ram')
    ram_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ram,))[0]['retail_price']
    gpu = request.cookies.get('gpu')
    gpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (gpu,))[0]['retail_price']
    if request.method == "POST":
        hdd = request.form.getlist("hdd")
        ssd = request.form.getlist("ssd")
        if len(ssd) > 2:
            error = ("You can only select up to 2 SSDs")
            return render_template("design-storage.html", cpu=cpu, cpu_price=int(cpu_price), motherboard=motherboard, motherboard_price=int(motherboard_price), ram=ram, ram_price=int(ram_price), gpu=gpu, gpu_price=int(gpu_price), HDDS=HDDS, SSDS=SSDS, error=error)
        storage_price = 0
        resp = make_response(redirect(url_for('design_cooler')))
        if hdd or hdd != None:
            resp.set_cookie("hdd", ",".join(hdd), httponly=True)
        else:
            resp.delete_cookie("hdd", path="/")
        if ssd or ssd != None:
            resp.set_cookie("ssd", ",".join(ssd), httponly=True)
        else:
            resp.delete_cookie("ssd", path="/")

        return resp
    
    return render_template("design-storage.html", cpu=cpu, cpu_price=int(cpu_price), motherboard=motherboard, motherboard_price=int(motherboard_price), ram=ram, ram_price=int(ram_price), gpu=gpu, gpu_price=int(gpu_price), HDDS=HDDS, SSDS=SSDS)

@app.route('/design-cooler', methods=['GET','POST'])
def design_cooler():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))[0]['retail_price']
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))[0]['retail_price']
    ram = request.cookies.get('ram')
    ram_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ram,))[0]['retail_price']
    gpu = request.cookies.get('gpu')
    gpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (gpu,))[0]['retail_price']
    hdds = request.cookies.get('hdd').split(",")
    if hdds or hdds != None or hdds != "":
        hdd_price = 0
        for hdd in hdds:
            price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (hdd,) )
            if price:
                hdd_price = price[0]['retail_price'] + hdd_price
            else:
                hdd_price = 0
    ssds = request.cookies.get('ssd').split(",")
    if ssds or ssds != None or hdds != "":
        ssd_price = 0
        for ssd in ssds:
            price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ssd,) )
            if price:
                ssd_price = price[0]['retail_price'] + ssd_price
            else:
                ssd_price = 0   
    storage_price = ssd_price + hdd_price
    storage = ssds + hdds
    coolers = run_query("SELECT component_name, retail_price FROM stock WHERE component_type = 'cooler' ORDER BY retail_price ASC")
    if request.method == "POST":
        cooler = request.form.get("cooler")
        resp = make_response(redirect(url_for('design_psu')))
        resp.set_cookie("cooler", cooler, httponly=True)
        resp.set_cookie("storage_price", str(storage_price), httponly=True)
        resp.set_cookie("storage", ",".join(storage), httponly=True)
        return resp

    return render_template("design-cooler.html", cpu=cpu, cpu_price=int(cpu_price), motherboard=motherboard, motherboard_price=int(motherboard_price), ram=ram, ram_price=int(ram_price), gpu=gpu, gpu_price=int(gpu_price), storage=storage, storage_price=int(storage_price), coolers=coolers)

@app.route('/design-case', methods=['GET','POST'])
def design_case():
    cpu = request.cookies.get('cpu')
    cpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (cpu,))[0]['retail_price']
    motherboard = request.cookies.get('motherboard')
    motherboard_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (motherboard,))[0]['retail_price']
    ram = request.cookies.get('ram')
    ram_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (ram,))[0]['retail_price']
    gpu = request.cookies.get('gpu')
    gpu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (gpu,))[0]['retail_price']
    storage_price = request.cookies.get('storage_price')
    storage = request.cookies.get('storage').split(",")
    coolers = request.cookies.get('cooler')
    cooler_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (coolers,))[0]['retail_price']
    psu = request.cookies.get('psu')
    psu_price = run_query("SELECT retail_price FROM stock WHERE component_name = ?", (psu,))[0]['retail_price']
    cases = run_query("SELECT component_name, retail_price, factor FROM stock WHERE component_type = 'case' ORDER BY retail_price ASC")
    motherboard_factor = run_query("SELECT factor FROM stock WHERE component_name = ?", (motherboard,))[0]['factor']
    filtered_cases = []
    if motherboard_factor == "ATX":
        for case in cases:
            case_factor = run_query("SELECT factor FROM stock WHERE component_name = ?", (case['component_name'],))[0]['factor']
            if case_factor == motherboard_factor:
                filtered_cases.append(case)
    elif motherboard_factor == "M-ATX":
        filtered_cases = cases

    
    if request.method == "POST":
        case = request.form.get("case")
        resp = make_response(redirect(url_for('design_name')))
        resp.set_cookie("case", case, httponly=True)
        print(case)
        return resp
    return render_template("design-case.html", cpu=cpu, cpu_price=int(cpu_price), motherboard=motherboard, motherboard_price=int(motherboard_price), ram=ram, ram_price=int(ram_price), gpu=gpu, gpu_price=int(gpu_price), storage=storage, storage_price=int(storage_price), cooler=coolers, cooler_price=cooler_price, psu=psu, psu_price=psu_price, cases=filtered_cases, )

@app.route('/design-summary', methods=['GET','POST'])
def design_summary():
    cpu = request.cookies.get('cpu')
    cpus = run_query("SELECT retail_price, component_name, socket_type FROM stock WHERE component_name = ?", (cpu,))
    motherboard = request.cookies.get('motherboard')
    motherboards = run_query("SELECT retail_price, component_name, socket_type, ram_type, factor FROM stock WHERE component_name = ?", (motherboard,))
    ram = request.cookies.get('ram')
    rams = run_query("SELECT retail_price, ram_type, component_name  FROM stock WHERE component_name = ?", (ram,))
    gpu = request.cookies.get('gpu')
    gpus = run_query("SELECT retail_price, component_name, ram_type FROM stock WHERE component_name = ?", (gpu,))
    storage_price = request.cookies.get('storage_price')
    storage = request.cookies.get('storage').split(",")
    storage_types = []
    for store in storage:
        if store:
            storage_type = run_query("SELECT factor FROM stock WHERE component_name = ?", (store,))[0]['factor']
            storage_types.append(storage_type)

    cooler = request.cookies.get('cooler')
    coolers = run_query("SELECT retail_price, socket_type, component_name FROM stock WHERE component_name = ?", (cooler,))
    psu = request.cookies.get('psu')
    psus = run_query("SELECT * FROM stock WHERE component_name = ?", (psu,))
    case = request.cookies.get('case')
    pc_name = request.cookies.get("pc_name")
    cases = run_query("SELECT component_name, retail_price, factor FROM stock WHERE component_name = ? ORDER BY retail_price ASC", (case,))
    cost = int(cpus[0]['retail_price']) + int(motherboards[0]['retail_price'] + int(rams[0]['retail_price']) + int(gpus[0]['retail_price'])  + int(storage_price) + int(coolers[0]['retail_price']) + int(psus[0]['retail_price']) + int(cases[0]['retail_price']))
    resp = make_response(render_template("design-summary.html", cpus=cpus, motherboards=motherboards, rams=rams, gpus=gpus, storage=storage, coolers=coolers, psus=psus, cases=cases, storage_price=int(storage_price),storage_types=storage_types, pc_name=pc_name))
    resp.set_cookie("cost",str(cost), httponly=True)
    return resp


@app.route('/design-save', methods=['POST'])
def design_save():
    if request.method == "POST":
        cpu = request.cookies.get("cpu")
        motherboard = request.cookies.get("motherboard")
        ram = request.cookies.get("ram")
        gpu = request.cookies.get("gpu")
        cooler = request.cookies.get("cooler")
        psu = request.cookies.get("psu")
        storage = request.cookies.get("storage").split(",")
        case = request.cookies.get("case")
        email = request.cookies.get("email")
        cost = request.cookies.get("cost")
        pc_name = request.cookies.get("pc_name")
        if not email:
            return redirect(url_for('login'))
        else:
            if not cpu or not motherboard or not ram or not gpu or not cooler or not psu or not storage or not case:
                return render_template("design-cpu", error="There was an error in designing your PC please restart.")
            limit = run_query("SELECT COUNT(email) as email_count FROM custom_builds WHERE email = (?)", (email,))[0]['email_count']
            print(limit)
            if int(limit) < 5:
                print("Inserting custom build into database")
                run_query("INSERT INTO custom_builds (cpu, motherboard, ram, storage, cooler, gpu, psu, pc_case, email, cost, name) VALUES (?,?,?,?,?,?,?,?,?,?,?)",(str(cpu), str(motherboard), str(ram), str(storage), str(cooler), str(gpu), str(psu), str(case), email, cost, pc_name))
                return render_template("custom.html", success=True)
            else:
                return render_template("custom.html", success="fail")
            
@app.route('/view-custom-builds')
def view_custom_builds():
    email = request.cookies.get('email')
    pcs = run_query("SELECT * FROM custom_builds WHERE email = ?",(email,))
    return render_template("view-custom-builds.html", pcs=pcs)    

@app.route('/remove-custom-build', methods=["POST"])
def remove_custom_build():
    id = request.form.get('id')
    custom_pc = run_query("DELETE FROM custom_builds WHERE id = ?", (id,))
    return redirect("/view-custom-builds")

@app.route('/design-name', methods=['GET','POST'])  
def design_name():
    error=False
    email = request.cookies.get("email")
    if request.method == "POST":
        pc_name = request.form.get("name")
        print(pc_name)
        if len(pc_name) > 20:
            return render_template("design-name.html", error="length")
        matching_pc = run_query("SELECT * FROM custom_builds WHERE name = ? and email = ?", (pc_name, email))
        if matching_pc == None:
            return render_template("design-name.html", error="match")

    
        resp = make_response(redirect(url_for('design_summary')))
        resp.set_cookie("pc_name", pc_name, httponly=True)
        print("cookie set")
        return resp

    return render_template("design-name.html")

@app.route('/custom-checkout', methods=["POST"])
def custom_checkout():
    name = request.cookies.get("pc_name")
    cost = request.cookies.get("cost")
    email = request.cookies.get("email")
    if run_query("SELECT * FROM basket WHERE user_email = ? AND name = ?", (email, name)):
        run_query("UPDATE basket SET quantity = quantity + 1 WHERE user_email = ? AND name = ?", (email, name))
    else:
        custom_info = run_query("SELECT * FROM custom_builds WHERE name = ? AND email = ?", (name, email))
        run_query("INSERT INTO basket (user_email, name, price, type, cpu, motherboard, ram, gpu, storage, cooler, psu, pc_case) VALUES (?, ?, ?,?,?,?,?,?,?,?,?,?)", (email, name, custom_info[0]['cost'], "Custom", custom_info[0]['cpu'], custom_info[0]['motherboard'], custom_info[0]['ram'], custom_info[0]['gpu'], custom_info[0]['storage'], custom_info[0]['cooler'], custom_info[0]['psu'], custom_info[0]['case']))
    return redirect("/basket")

@app.route('/custom-basket', methods=["POST"])
def custom_basket():
    email = request.cookies.get("email")
    id = request.form.get("id")
    custom_info = run_query("SELECT * FROM custom_builds WHERE id = ?", (id,))
    if run_query("SELECT * FROM basket WHERE user_email = ? AND name = ?", (email, custom_info[0]['name'])):
        run_query("UPDATE basket SET quantity = quantity + 1 WHERE user_email = ? AND name = ?", (email, custom_info[0]['name']))
    else:
        run_query("INSERT INTO basket (user_email, name, price, type, cpu, motherboard, ram, gpu, storage, cooler, psu, pc_case) VALUES (?, ?, ?,?,?,?,?,?,?,?,?,?)", (email, custom_info[0]['name'], custom_info[0]['cost'], "Custom", custom_info[0]['cpu'], custom_info[0]['motherboard'], custom_info[0]['ram'], custom_info[0]['gpu'], custom_info[0]['storage'], custom_info[0]['cooler'], custom_info[0]['psu'], custom_info[0]['pc_case']))
    return redirect("/view-custom-builds")

@app.route('/compare-customs', methods=['GET', 'POST'])
def compare_customs():
    email = request.cookies.get("email")
    show=False
    customs = run_query("SELECT * FROM custom_builds WHERE email = ?", (email,))
    prebuilds = run_query("SELECT * FROM products")
    if request.method == "POST":
        prebuild = request.form.get("prebuild")
        custom = request.form.get("custom")
        if prebuild and custom:
            
            prebuild_info = run_query("SELECT * FROM products WHERE name = ?", (prebuild,))
            custom_info = run_query("SELECT * FROM custom_builds WHERE email = ? AND name = ?", (email, custom, ))
        
            return render_template("compare-customs.html", custom_info=custom_info, prebuild_info=prebuild_info, customs=customs, prebuilds=prebuilds, show=True)
        return render_template("compare-customs.html", customs=customs, prebuilds=prebuilds, show=False)

    return render_template("compare-customs.html", customs=customs, prebuilds=prebuilds, show=show)


@app.route('/orders', methods=['GET'])
def orders():
    email = request.cookies.get('email')
    orders = run_query("SELECT * FROM orders WHERE email = ?", (email,))
    return render_template("orders.html", orders=orders)

@app.route('/help',methods=['GET','POST'])
def help():
    name = request.cookies.get('firstname')
    email = request.cookies.get('email')
    success=False
    if request.method == "POST":
        user_request = request.form.get('request')

        sender_email = "timcheese129@gmail.com"      
        sender_password = "pvlgqsmylakudwlo"     
        receiver_email = "timcheese129@gmail.com"  

        msg = EmailMessage()
        msg.set_content(f"New help request:\n\n{user_request}")
        msg['Subject'] = f"New Help Request From {email}"
        msg['From'] = sender_email
        msg['To'] = receiver_email

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)
            return render_template("help.html", success="True", name=name)
        except Exception as e:
            return f"Failed to send request: {e}"

    return render_template("help.html")
@app.route('/account', methods=['GET'])
def account():
    firstname = request.cookies.get('firstname')
    email = request.cookies.get('email')
    return render_template("account.html", firstname=firstname, email=email)

from flask import Flask, render_template, request, redirect, flash
from flaskext.mysql import MySQL
from datetime import datetime, timedelta, time

app=Flask(__name__)
app.secret_key="yo"
mysql= MySQL()
app.config['MYSQL_DATABASE_USER']='root'
app.config['MYSQL_DATABASE_PASSWORD']= 'bangtan'
app.config['MYSQL_DATABASE_DB']= 'dbmsproject'
app.config['MYSQL_DATABASE_HOST']='localhost'
mysql.init_app(app)

conn=mysql.connect()


@app.route('/')
def index():
	return render_template('index.html')


@app.route('/vehicles', methods=['GET','POST'])
def info():
	if request.method=='POST':
		vehid=request.form.get("vehicle_id")
		name=request.form.get("cust_name")
		dateofbirth=request.form.get("dob")
		number=request.form.get("phone")
		mail=request.form.get("email")
		aad=request.form.get("aadhar")
		add=request.form.get("address")
		cursor=conn.cursor()
		query= "insert into customer(cust_name,dob,vehicle_id,phone,email,aadhar,address) values(%s,%s,%s,%s,%s,%s,%s)"
		cursor.execute(query,(name,dateofbirth,vehid,number,mail,aad,add))
		conn.commit()
		return redirect('/vehicles/details')
	return render_template('bookcar.html')


@app.route('/vehicles/details', methods=['GET', 'POST'])
def show():
	today = datetime.today().strftime('%Y-%m-%d')
	del_date = datetime.now().today() + timedelta(days=7)
	new_price=0
	
	cursor=conn.cursor()
	#query="select * from customer where cust_id in (select MAX(cust_id) from customer)"
	cursor.callproc('getprocedure')
	#cursor.execute(query)
	dataC=cursor.fetchall()
	CRow=dataC[0]
	
	cursor.execute("select * from vehicle where vehicle_id = %s", CRow[2])
	dataV=cursor.fetchall()
	VRow=dataV[0]
	new_price= (VRow[3]+(0.18*VRow[3]))
	
	
	queryb="insert into booking(booked_date, del_date, vehicle_id, price, cust_id) values (%s,%s,%s,%s,%s)"
	cursor.execute(queryb,(today,del_date,CRow[2],new_price,CRow[0]))
	conn.commit()
	
	cursor.execute("select * from booking where booking_id in ( select MAX(booking_id) from booking)")
	dataB=cursor.fetchall()
	BRow=dataB[0]
	conn.commit()

	if request.method == 'POST':
		decision = request.form.get('decision')
		if decision == '0':
			
			cursor.execute("delete from customer order by cust_id desc limit 1")
			cursor.execute("delete from booking order by booking_id desc limit 1")
			conn.commit()
			return redirect('/')
		else:
			cursor.execute("update vehicle set quantity=quantity-1 where vehicle_id =%s", CRow[2])
			conn.commit()
			return redirect('/payment')



	return render_template('booking_details.html', VRow=VRow, CRow=CRow, BRow=BRow)


@app.route('/payment')
def pay():
	return render_template('payment.html')


@app.route('/login', methods=['GET','POST'])
def log():
	if request.method=='POST':
		if request.form['submit_button']=="Login to Track":
			empid= request.form.get("emp_id")
			eid=int(empid)
			pas=request.form.get("passwordd")
			cursor=conn.cursor()
			cursor.execute("select passwordd from login_credentials where emp_id=%s",eid)
			data=cursor.fetchall()
			for row in data:
				if row[0]==pas:
					return redirect('login/trace')
				else:
					flash("ENTER VALID CREDENTIALS")

		elif request.form['submit_button']=="Login to add service":
			empid= request.form.get("emp_id1")
			eid=int(empid)
			pas=request.form.get("passwordd1")
			cursor=conn.cursor()
			cursor.execute("select passwordd from login_credentials where emp_id=%s",eid)
			data=cursor.fetchall()
			for row in data:
				if row[0]==pas:
					cursor.execute("insert into service(emp_id) values (%s)", eid)
					conn.commit()
					return redirect('login/addnewservice')
				else:
					flash("ENTER VALID CREDENTIALS")

	return render_template('loginpage.html')


@app.route('/login/trace', methods=['GET','POST'])
def tracing():
	if request.method=="POST":
		date=request.form.get("date")
		serviceno=request.form.get("serviceNum")
		cursor=conn.cursor()
		cursor.execute("select * from service where service_num=%s", serviceno)
		data=cursor.fetchall()
		SRow=data[0]
		if str(date)==str(SRow[4]):
			cursor.execute("update temp_bill set service_num = %s",serviceno)
			conn.commit();
			return redirect('login/trace/billing')
		else:
			error="Error"
			flash("Oops service pending, try again later!")

	return render_template('tracepage.html')

		
@app.route('/login/addnewservice', methods=['GET','POST'])
def serv():
	cursor = conn.cursor()

	if request.method=='POST':
		cust_id=request.form.get("cust_id")
		vehid=request.form.get("vehicle_id")
		date=request.form.get("date_given")	
		odo_read=request.form.get("odo_reading")
		part_list=request.form.getlist("spareParts")

		total_cost = 1000
		for part in part_list:
			cursor.execute("select cost from spare_parts where part_id = %s", part)
			dataPA= cursor.fetchall()
			dataPA2=dataPA[0]
			total_cost += dataPA2[0]
		cursor.execute("select * from service order by service_num desc limit 1")
		data = cursor.fetchall()
		SRow = data[0]
		cursor.execute("insert into billing(cust_id, vehicle_id,total_amt,service_num) values(%s,%s,%s,%s)",( cust_id,vehid,total_cost,SRow[0]))
		cursor.execute("update service set exp_del_date = DATE_ADD(%s, INTERVAL 2 DAY) where service_num=%s",(date, SRow[0]))
		cursor.execute("update service set next_ser_date = DATE_ADD(%s, INTERVAL 3 MONTH) where service_num=%s", (date,SRow[0]))
		query_vars = [SRow[0], len(part_list)] 
		
		while len(part_list)!=5:
			part_list.append("NULL")
		
		query_vars.extend(part_list)
		cursor.execute("insert into parts_used values(%s, %s, %s, %s, %s, %s, %s)", tuple(query_vars))
		cursor.execute("update service set vehicle_id=%s, cust_id=%s, date_given=%s, odo_read=%s where service_num=%s", (vehid, cust_id, date, odo_read, SRow[0]))
		

		conn.commit()

	return render_template('addnewservice.html')

	

@app.route('/login/trace/billing')
def bil():
	cursor=conn.cursor();
	cursor.execute("select * from temp_bill");
	dataB=cursor.fetchall()
	BillRow=dataB[0]
	print(dataB, dataB[0], BillRow[0])
	cursor.execute("select * from billing where service_num= %s", BillRow[0])
	dataBI=cursor.fetchall()
	print(dataBI)
	BIRow=dataBI[0]
	cursor.execute("select * from customer where cust_id=%s", BIRow[1])
	dataC=cursor.fetchall()
	CRow=dataC[0]
	cursor.execute("select * from vehicle where vehicle_id=%s", BIRow[2])
	dataV=cursor.fetchall()
	VRow=dataV[0]
	cursor.execute("select * from parts_used where service_num=%s", dataB[0])
	dataPU=cursor.fetchall()
	dataSP=[]
	PURow=dataPU[0]
	for i in range(PURow[1]):
		cursor.execute("select * from spare_parts where part_id=%s", PURow[i+2])
		dataSP.append(cursor.fetchall())

	dataSpt=tuple(dataSP)
	dataSP=[]
	for tup in dataSpt:
		dataSP.append(tup[0])

	today_date=datetime.today()
	cursor.execute("select * from service where service_num=%s", BillRow[0])
	dataS=cursor.fetchall()
	SRow=dataS[0]
	cursor.execute("select emp_name from employee where emp_id=%s", SRow[7])
	dataE=cursor.fetchall()
	emp_name=dataE[0]

	return render_template('billing.html', BIRow=BIRow, CRow=CRow, VRow=VRow, dataSP=dataSP, SRow=SRow, emp_name=emp_name[0], today_date=today_date)



if __name__ == '__main__':
	app.run(host='localhost', port=5000, debug=True)




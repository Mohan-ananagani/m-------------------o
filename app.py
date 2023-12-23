from flask import Flask,request,render_template,url_for,redirect,flash,abort,session,send_file

import flask_excel as excel
import mysql.connector
from flask_session import Session
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from key import secret_key,salt,salt2,salt3
from cmail import sendmail
from io import BytesIO
from otp import adotp
import os
mydb=mysql.connector.connect(host='localhost',user='root',password='Admin',db='records')
app=Flask(__name__)
excel.init_excel(app)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
@app.route('/')
def index():
    return render_template('home.html')
@app.route('/home')
def home():
    return render_template('afterloginhome.html')
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        name=request.form['name']
        phone=request.form['phone']
        email=request.form['email']
        address=request.form['address']
        password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from sign where email=%s',[email])
            count=cursor.fetchone()[0]
            print(count)
            if count==1:
                raise Exception
        except Exception as e:
            flash('User already registered')
            return redirect(url_for('index'))
        else:
            data={'name':name,'email':email,'phone':phone,'address':address,'password':password}
            subject='The confirmation link has sent to your Email'
            body=f"Click the link to confirm{url_for('confirm',token=token(data,salt=salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Link has sent to this Mail')
            return redirect(url_for('login'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('email'):
        return redirect(url_for('index'))
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email,password from sign where email=%s and password=%s',[email,password])
        count=cursor.fetchone()
        if count==(email,password):
            session['email']=email
            if not session.get(email):
                session[email]={}
            flash(f'{email} you have successfully logged in')
            return redirect(url_for('home'))
    return render_template('login.html')
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=3600)
    except Exception as e:
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into sign values(%s,%s,%s,%s,%s)',[data['name'],data['phone'],data['email'],data['address'],data['password']])
        mydb.commit()
        cursor.close()
        flash('Details Registered successfully')
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('email'):
        session.pop('email')
        flash('logged out successfully')
        return redirect(url_for('login'))
    return redirect(url_for('login'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from sign where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        try:
            if count!=1:
                raise Exception
        except Exception as e:
            flash('Pls Register for the application')
            return redirect(url_for('index'))
        else:
            subject='Reset link for application'
            body=f"The reset link for application: {url_for('uforgot',token=token(email,salt=salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Reset Link has sent to give email pls check.')
            return redirect(url_for('forgot'))
    return render_template('emailforgot.html')
@app.route('/uforgot/<token>',methods=['GET','POST'])
def uforgot(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Reset link expired')
    else:
        if request.method=='POST':
            npassword=request.form['npassword']
            cpassword=request.form['cpassword']
            if npassword==cpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update sign set password=%s where email=%s',[npassword,data])
                mydb.commit()
                cursor.close()
                flash('Password has updated')
                return redirect(url_for('login'))
            else:
                flash('Mismatched password')
                return render_template('forgot.html')
        return render_template('forgot.html')
@app.route('/addnote',methods=['GET','POST'])
def addnote():
    if session.get('email'):
        if request.method=='POST':
            name=request.form['name']
            description=request.form['description']
            email=session.get('email')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into note(note_id,name,description,email) values(uuid_to_bin(uuid()),%s,%s,%s)',[name,description,email])      
            mydb.commit()
            cursor.close()
            flash('Your notes has successfully inserted')
            return redirect(url_for('home'))
        return render_template('note.html')
    else:
        return redirect(url_for('login'))
@app.route('/note')
def note():
    if session.get('email'):
        email=session.get('email')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(note_id),name,date from note where email=%s',[email])
        count1=cursor.fetchall()
        return render_template('teb.html',count1=count1)
    return redirect(url_for('login'))
@app.route('/vnote/<noteid>',methods=['GET','POST'])
def vnote(noteid):
    email=session.get('email')
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select name,description from note where note_id=uuid_to_bin(%s)',[noteid])
    count1=cursor.fetchone()
    return render_template('viewn.html',count1=count1)
@app.route('/update/<noteid>',methods=['GET','POST'])
def update(noteid):
    if session.get('email'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select name,description from note where note_id=uuid_to_bin(%s)',[noteid])
        count1=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            name=request.form['name']
            description=request.form['description']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update note set name=%s,description=%s where note_id=uuid_to_bin(%s)',[name,description,noteid])
            mydb.commit()
            cursor.close()
            flash('Your notes was updated successfully')
            return render_template('note_update.html',count1=count1)
    return render_template('note_update.html',count1=count1)
@app.route('/delete/<noteid>')
def delete(noteid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from note where note_id=uuid_to_bin(%s)',[noteid])
    mydb.commit()
    cursor.close()
    return redirect(url_for('note'))
@app.route('/addfile',methods=['GET','POST'])
def addfile():
    if session.get('email'):
        if request.method=='POST':
            data=request.files.getlist('file')
            print(data)
            email=session.get('email')
            for i in data:
                file_ext=i.filename.split('.')[-1]
                file_data=i.read()
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into file(file_id,file_extension,data,email) values(uuid_to_bin(uuid()),%s,%s,%s)',[file_ext,file_data,email])
                mydb.commit()
                cursor.close()
            flash('your file  successfully added')
            return redirect(url_for('home'))
    return render_template('file_upload.html')
@app.route('/file/<fileid>')
def fileview(fileid):
    if session.get('email'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select file_extension,data from file where file_id=uuid_to_bin(%s)',[fileid])
        ext,data=cursor.fetchone()
        data=BytesIO(data)
        filename=f'attachment.{ext}'
        return send_file(data,download_name=filename,as_attachment=False)
    return redirect(url_for('file'))

@app.route('/viewfile',methods=['GET','POST'])
def vfile():
    if session.get('email'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(file_id),date from file where email=%s',[session.get('email')])
        data=cursor.fetchall()
        #data=BytesIO(data)
        #filename=f'attachment.{ext}'
        return render_template('tab.html',data=data)
    return redirect('login')
@app.route('/download/<fileid>')
def download(fileid):
    if session.get('email'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select file_extension,data from file where file_id=uuid_to_bin(%s)',[fileid])
        ext,data=cursor.fetchone()
        data=BytesIO(data)
        filename=f'attachment.{ext}'
        return send_file(data,download_name=filename,as_attachment=True)
    return redirect(url_for('file'))
@app.route('/fdelete/<fileid>')
def fdelete(fileid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from file where file_id=uuid_to_bin(%s)',[fileid])
    mydb.commit()
    cursor.close()
    flash('file have been deleted successfully')
    return redirect(url_for('vfile'))
@app.route('/excell')
def excell():
    if session.get('email'):
        email=session.get('email')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select name,description,date from note where email=%s',[email])
        counter=cursor.fetchall()
        cursor.close()
        columns=['name','Description','Date']
        array_data=[list(i) for i in counter]
        array_data.insert(0,columns)
        #print(array_data)
        response = excel.make_response_from_array(array_data,'xlsx',filenmae='Notes')
        print(response)
        return response
    else:
        return redirect(url_for('login'))
app.run(debug=True,use_reloader=True,port=8000)
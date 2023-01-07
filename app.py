#importing required packages
from datetime import datetime
import time
import gspread
import flask
import random
from flask_mail import Mail,Message
import keygenerator
import postgres
import string
from Form_model import SignupForm
from Quiz.test import test
from Admin.admin import admin
from Dashboard.profile import profile
#configuring flask app
app = flask.Flask(__name__, template_folder="Templates",static_folder='Static')

app.config['SECRET_KEY']='xd1ssgZnh\xe51M\x898\x13e\xbdt'+str(datetime.today().strftime("%d/%m/%Y"))
mail=Mail(app)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'apteeproject@gmail.com'
app.config['MAIL_PASSWORD'] = keygenerator.get_email_pass()
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

app.register_blueprint(admin,url_prefix='/admin_panel/')
app.register_blueprint(test,url_prefix='/test/')
app.register_blueprint(profile,url_prefix='/Dashboard/')



def send_email(Header,html,email,param):
        msg = Message(
                        Header,
                        sender ='apteeproject@gmail.com',
                        recipients = [email]
                        )
        msg.html=flask.render_template(html,name=param[0],OTP=param[1],link=param[2])
        mail.send(msg)
gc = gspread.service_account_from_dict(keygenerator.get_db_auth())
@app.route('/', methods =['POST', 'GET'])
def home():
        if flask.request.method=='GET':
                flask.session.pop('last_page',None)
        form = SignupForm(flask.request.form)
        if 'id' in flask.session:
                id=flask.session['id']
                return flask.render_template('index.html',form=form,id=id)
        else:
                if form.email_id.data:
                        postgres_find_query="""
                        with coins as (SELECT c.clientid, sum(c.coin_in::INTEGER)-sum(c.coin_out::INTEGER) as coin from clients.coin_history c
                        GROUP by c.clientid)
                        SELECT d.clientid,d.email_id,d.cl_password,d.client_name,co.coin from clients.details as d
                        LEFT JOIN coins co on d.clientid = co.clientid
                        Where lower(d.email_id) like '{0}'
                        LIMIT 1;
                        """.format(form.email_id.data.lower())
                        #print(postgres_find_query)
                        res,err=postgres.postgres_connect(postgres_find_query,commit=0)
                        details=[list(e) for e in res]
                        if len(details)>0 and len(err)==0:
                                if form.password.data == details[0][2]:
                                        flask.session['id']=details[0][0]
                                        if 'last_page' in flask.session:
                                                print(flask.session['last_page'])
                                                if flask.session['last_page']==1:
                                                        flask.session.pop('last_page',None)
                                                        return flask.redirect(flask.url_for("test.Test"))
                                        else:
                                                return flask.render_template('index.html',form=form,message="Logged in Successfully as : "+details[0][3],id=flask.session['id'],alert_colour=1)
                                else:
                                        return flask.render_template('index.html',form=form,message="Password incorrect",alert_colour=0)
                        else:
                                return flask.render_template('index.html',form=form,message="Please Register First!",alert_colour=1)
                else:
                        return flask.render_template('index.html',form=form)
        
@app.route('/account_creation',methods=['GET','POST'])
def account():
        form = SignupForm(flask.request.form)
        coins=0
        if 'id' in flask.session:
                id=flask.session['id']
                return flask.render_template('index.html',form=form,id=id)
        if 'attempt' in flask.session:
                if flask.session['attempt'].split(',')[1] == 1:
                        coins=10
                else:
                        coins=0
        if form.email_id.data:
                postgres_find_query="""
                        SELECT cl.clientid,cl.email_id,cl.cl_password,cl.client_name from clients.details cl 
                        where 
                        lower(cl.email_id) like '{0}'
                        """.format(form.email_id.data.lower())
                res,err=postgres.postgres_connect(postgres_find_query,commit=0)
                details=[list(e) for e in res]
                if len(details)>0:
                        return flask.render_template('index.html',form=form,alert_colour=1,message="You already have an account!")
                else:
                        time.sleep(random.randint(1,3))
                        OTP=random.randint(10000,99999)
                        id="CL"+datetime.now().strftime("%d%m%Y%H%M%S")
                        send_email(string.capwords(form.name.data)+' here is the otp for your Aptee account','registration_email.html',form.email_id.data.lower(),
                                param=[string.capwords(form.name.data),OTP,('127.0.0.1/account_creation/'+str(id))])
                        postgres_insert_query="""INSERT INTO clients.details (clientid,email_id,client_name,cl_password,dob,target_exam,gender,college,college_location,client_course,semester,email_verified)
                                        VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}','{10}','{11}','{12}')
                                        """.format(id,form.email_id.data.lower(),string.capwords(form.name.data),form.password.data,
                                        str(form.DOB.data),form.target.data,form.gender.data,form.college.data,
                                        form.college_location.data,form.course.data,form.semester.data,OTP)
                        a=postgres.postgres_connect(postgres_insert_query,commit=1)
                        
                        if a:  
                                if coins!=0:
                                        postgres_insert_query = """
                                            INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                            VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)
                                            """.format(flask.session['id'],flask.session['attempt'].split(',')[0],10,0)
                                        a=postgres.postgres_connect(postgres_insert_query,commit=1)
                                return flask.render_template('index.html',form=form,alert_colour=0,message="Account Created Successfully!",id=id)
                        else:
                                return flask.render_template('register.html',form=form,alert_colour=0,message="We had some problems setting you up!")
        else:
               return flask.render_template('register.html',form=form)

@app.route('/contact_us',methods=['POST'])
def contact_us():
        form = SignupForm(flask.request.form)
        Client_ip=flask.request.environ.get('HTTP_X_FORWARDED_FOR', flask.request.environ['REMOTE_ADDR'])
        sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1CyWjl6Y5Gi_e3z7A8wtw-qOaBe3GvCD4sqWWvaMubXY/edit?usp=sharing')
        wks=sh.worksheet("Contact_us")
        print(flask.request.form)
        if flask.request.form:
                 wks.append_row([flask.request.form.get('name'),flask.request.form.get('email'),flask.request.form.get('subject'),
                 flask.request.form.get('body'),Client_ip,str(datetime.now())])      
        return flask.render_template('index.html',form=form,message="We have Received Your Message!",alert_colour=0)
@app.route('/comming_soon',methods=['GET'])
def comming_soon():
        form = SignupForm(flask.request.form)
        return flask.render_template('Comming_soon.html',form=form)

@app.route('/logout',methods=['GET','POST'])
def logout():
        flask.session.pop('id',None)
        flask.session.pop('attempt',None)
        return flask.redirect(flask.url_for("home"))

if __name__ == '__main__':
    app.run(debug = False)
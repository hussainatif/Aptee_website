import flask
import gspread
import keygenerator
from Form_model import SignupForm
import postgres
import random
test= flask.Blueprint('test', __name__,template_folder='../Templates',static_folder='../Static')
gc = gspread.service_account_from_dict(keygenerator.get_db_auth())
@test.route('/notif/<msg>&<alert>',methods=['GET','POST'])
@test.route('/',methods=['GET','POST'])
def Test(msg="",alert=0):
        #add login verification
    
    form = SignupForm(flask.request.form)
    if 'id' in flask.session:
        if len(msg):
            return flask.render_template('select_exam.html',form=form,id=flask.session['id'],message=msg,alert_colour=alert)    
        return flask.render_template('select_exam.html',form=form,id=flask.session['id'])
    else:
        flask.session['last_page']=1
        return flask.render_template('select_exam.html',form=form)

@test.route('/Random_Test/',methods=['GET','POST'])
@test.route('/Daily_Test/<qid>',methods=['GET','POST'])
def daily(qid=0):
    form = SignupForm(flask.request.form)
    sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1vYStVgetyDmsbZ-AXfiSvTRXwpTxsLaH4FFa1weFZ-I/edit?usp=sharing')
    wks=sh.worksheet("Question_Details")
    if qid==0:
        test_row=random.randint(2,30)
        test_id='RANDOM'
    else:
        test_id='RECOMMEND'
        test_row=int(qid[2:])+1
    row =wks.row_values(test_row)
    #row=wks.row_values(random.randint(2,16))
    #print(row)
    if 'attempt' in flask.session:
        return flask.render_template('register.html',form=form,message="Please Sign up or Sign in to Continue with the Assessment")
    if 'id' in flask.session:
        postgres_find_query="""
        with coins as (SELECT c.clientid, sum(c.coin_in::INTEGER)-sum(c.coin_out::INTEGER) as coin from clients.coin_history c GROUP by c.clientid)
        SELECT d.client_name,d.college,co.coin from clients.details as d
        LEFT JOIN coins co on co.clientid=d.clientid
        WHERE d.clientid like '{0}'
        LIMIT 1;""".format(flask.session['id'])
        res,err=postgres.postgres_connect(postgres_find_query,commit=0)
        if len(err)==0:
            client=[list(e) for e in res]
            if flask.request.form:

                if flask.request.form.get('mcq'):
                    submitted=1
                    if flask.request.form.get('mcq')==row[12]:
                        correct=True
                    else:
                        correct=False
                else:
                    correct=0
                    submitted=0
                postgres_insert_query = """
                                            INSERT INTO 
                                            clients.attempts(questionid,clientid,attempt_time,correct,time_taken,optimum_time,question_subtopic,question_level,question_length,submitted,test_id)
                                            VALUES ('{0}','{1}',CURRENT_TIMESTAMP,'{2}','{3}','{4}','{5}','{6}','{7}',{8},'{9}')
                                            """.format(row[0],flask.session['id'],correct,(int(flask.request.form.get('Time_sheet'))/1000),\
                                                                             row[15],row[4],row[5],row[6],submitted,test_id)
                a=postgres.postgres_connect(postgres_insert_query,commit=1)
                if a:
                    postgres_insert_query = """
                                            INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                            VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)
                                            """.format(flask.session['id'],row[0],10,0)
                    a=postgres.postgres_connect(postgres_insert_query,commit=1)
                    return flask.redirect(flask.url_for("test.Test",msg="You Have Completed The Test",alert=1))
                    #return flask.render_template('select_exam.html',form=form,message="You Have Completed the Test",alert_colour=1,id=flask.session['id'])
                else:
                    return flask.redirect(flask.url_for("test.Test",msg="We Couldn't Save your Data",alert=0))

            else:
                return flask.render_template('daily_questions.html',Client=client[0],Question=row,form=form)
        else: 
            return flask.redirect(flask.url_for("test.Test",msg="We've Encountered some Error Please Try Again",alert=0))
    else:
        if flask.request.form:
            if flask.request.form.get('mcq')==row[12]:
                    correct=1
            else:
                    correct=0
            flask.session['attempt']=str(int(row[0][2:]))+','+str(correct)+','+str(int(flask.request.form.get('Time_sheet'))/1000)
            return flask.render_template('select_exam.html',form=form,message="Sign up or login to Claim your coins!",alert_colour=1)
        else:
            return flask.render_template('daily_questions.html',Question=row,form=form)

@test.route('/custom_test/testID=<testId>',methods=['GET','POST'])
def customTest(testId):
    if 'id' not in flask.session:
        flask.session['last_page']=1
        return flask.redirect(flask.url_for("test.Test",msg="That Test Isn't Available Please Try Again!",alert=0))
    else:
        sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1vYStVgetyDmsbZ-AXfiSvTRXwpTxsLaH4FFa1weFZ-I/edit?usp=sharing')
        wks=sh.worksheet("Test")
        test_row=int(testId[2:])+1
        row =wks.row_values(test_row)
        if len(row)==0:
            return flask.redirect(flask.url_for("test.Test",msg="That Test Isn't Available Please Try Again!",alert=0))
        else:
            return flask.render_template('Exam_dashboard.html',show_ques=0,Questions=','.join(row))
@test.route('/exam_submit/',methods=['POST'])
def exam_submit():
    form= SignupForm(flask.request.form)
    if 'id' in flask.session:
        if flask.request.form:
            if flask.request.form.get('First_Q'):
                try:
                    Questions=flask.request.form.get('Questions').split(',')
                    Status='1'
                    return flask.render_template('Question_submit.html',next_Q=Questions[len(Status.split(','))],
                    Questions=','.join(Questions),Status=Status)
                except Exception as e:
                    print("First Question Exception")
                    print(e)
                    return flask.redirect(flask.url_for("test.Test",msg="We've Encountered some Error Please Try Again",alert=0))
            else:
                try:
                    this_Q=flask.request.form.get('Question')
                    Questions=flask.request.form.get('Questions').split(',')
                    Status=flask.request.form.get('Status').split(',')
                    time=flask.request.form.get('Time')
                    row=this_Q.split('||')
                    if flask.request.form.get('mcq') == None:
                        Status.append('0')
                        correct=False
                    elif flask.request.form.get('mcq')==row[12]:
                        correct=True
                        Status.append('1')
                    else:
                        correct=False
                        Status.append('1')
                    postgres_insert_query = """
                                            INSERT INTO clients.attempts(questionid,clientid,attempt_time,correct,time_taken,optimum_time,question_subtopic,question_level,question_length,submitted,test_id)
                                            VALUES ('{0}','{1}',CURRENT_TIMESTAMP,'{2}','{3}','{4}','{5}','{6}','{7}',{8},'{9}')
                                            """.format(row[0],flask.session['id'],correct,time,row[15],row[4],row[5],row[6],Status[-1],Questions[0])
                    a=postgres.postgres_connect(postgres_insert_query,commit=1)
                    if a:
                        postgres_insert_query = """
                                            INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                            VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)
                                            """.format(flask.session['id'],row[0],10,0)
                        a=postgres.postgres_connect(postgres_insert_query,commit=1)
                    else:
                        return flask.redirect(flask.url_for("test.Test",msg="That Test Isn't Available Please Try Again!",alert=0))
                    if len(Status)==16:
                        postgres_insert_query = """
                                            INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                            VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)
                                            """.format(flask.session['id'],Questions[0],100,0)
                        a=postgres.postgres_connect(postgres_insert_query,commit=1)
                        return flask.redirect(flask.url_for("test.Test",msg="You Have Completed The Test!",alert=1))
                        return flask.render_template('select_exam.html',message="You Have Completed The Test!",alert_colour=1,form=form,id=flask.session['id'])
                    #print(Questions,Status)
                    return flask.render_template('Question_submit.html',next_Q=Questions[len(Status)],Questions=','.join(Questions),
                                                                    Status=','.join(Status))
                except Exception as e:
                    print(e)
                    print("Submit Exception")
        return flask.redirect(flask.url_for("test.Test",msg="We have encountered an error please Try Again!",alert=1))
        
    return flask.redirect(flask.url_for("test.Test",msg="Please Login to Continue!",alert=0))
   
@test.route('/exam_dashboard/<qno>',methods=['GET','POST'])
def exam_dashboard(qno):
    form = SignupForm(flask.request.form)
    if 'id' in flask.session:
        if flask.request.form:
            try:
                Questions=flask.request.form.get('Questions').split(',')
                Status=flask.request.form.get('Status').split(',')
                #print(Questions,Status)
                sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1vYStVgetyDmsbZ-AXfiSvTRXwpTxsLaH4FFa1weFZ-I/edit?usp=sharing')
                wks=sh.worksheet("Question_Details")
                test_row=int(qno[2:])+1
                row =wks.row_values(test_row)
                timer=int(row[15])
                return flask.render_template('Exam_dashboard.html',Row=row,Ques='||'.join(row),timer=timer,
                Questions=','.join(Questions),Status=','.join(Status),status=Status,show_ques=1)
            except Exception as e:
                print("Dashboard Exception")
                print(e)
                return flask.redirect(flask.url_for("test.Test",msg="We have encountered an error please Try Again!",alert=1))
        return flask.redirect(flask.url_for("test.Test",msg="We have encountered an error please Try Again!",alert=1))
    return flask.redirect(flask.url_for("test.Test",msg="Please Login to Continue!",alert=0))
@test.route('/exit_quiz/',methods=['GET','POST'])
def exit():
    return flask.redirect(flask.url_for("test.Test",msg="You Have Exited the Quiz",alert=0))
    
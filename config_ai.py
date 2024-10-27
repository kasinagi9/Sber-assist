from imghdr import tests
import time
import json
from typing import Dict
from typing_extensions import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from typing import Literal
from pydantic import BaseModel, Field
from langchain_community.chat_models import GigaChat
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain import hub
from langchain_core.output_parsers import StrOutputParser
from route_ai import *


token = '7819611153:AAFbmApijkMPEFfJoLhLF6eYtbM0-Fxt6co'
creds = "OGYzYWIxZmEtNGY3Yy00YTRkLWJmZGItYWQzNjJiZDU1ODYwOmExZTJjNDJhLTFiYTgtNDE1Yy04M2QwLTAwNDdhZTQ5NDE3Mg=="
class GraphState(TypedDict):
    args: Dict
    question: str
    generation: str
    context: str


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    qtype: Literal["info_clinic", "appointment", "info_doctor", "info_free_date", "time_appointment", "i_feel_pain", "what_him_heal", "to_do"] = Field(
        ...,
        description="Given a user question choose to route it to web search or a vectorstore.",
    )


def get_context(question, state = GraphState, dict = {}):
    system = """
    Твоя задача соотнести вопрос пользователя с одной из категорий:
    1. appointment - Запись на приём к врачу \n
    2. info_free_date - Вопрос про время приема у врача \n
    3. info_doctor - Список врачей \n
    4. info_clinic - Список клиник \n
    5. i_feel_pain - Человек чувствует дискомфорт или симптомы болезни\n
    6. what_him_heal - Вопрос про то какие симптомы лечит врач \n
    7. to_do - Вопрос куда и когда записан пользователь\n
    8. how-to-appointment - Вопрос о том как записаться\n
    В ответ написать к какой категории относится вопрос
    """

    chat = GigaChat(
        model="GigaChat",
        credentials=creds,
        scope="GIGACHAT_API_PERS",  # "GIGACHAT_API_PERS",
        verify_ssl_certs=False,

        temperature=0.1
    )

    structured_llm_router = chat.with_structured_output(RouteQuery)
    type_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "User question: {question}"),
        ]
    )

    categorize_llm = type_prompt | structured_llm_router


    print("---ROUTE QUESTION---")
    source = categorize_llm.invoke({"question": question})
    print(source['qtype'])

    if source['qtype'] == "info_clinic":
        print("---ROUTE QUESTION TO INFO CLINIC---")
        return info_clinic()
    elif source['qtype'] == "appointment":
        return appointment(question, dict = dict)
    elif source['qtype'] == "i_feel_pain":
        return i_feel_pain()
    elif source['qtype'] == "info_doctor":
        return find_doctors()
    elif source['qtype'] == "info_free_date":
        print("---ROUTE QUESTION TO INFO FREE DATE---")
        return info_free_date()
    elif source['qtype'] == "what_him_heal":
        print("---ROUTE QUESTION TO what_him_heal---")
        return find_doctors()
    elif source['qtype'] == "to_do":
        print("---ROUTE QUESTION TO to_do ---")
        return to_do(dict)


def info_clinic():
    graphql_search_clinic = {
        "operationName": "",
        "variables": {},  # No dollar sign here
        "query": """query {
          searchClinic{
            elems{
              name
                    classOfficeList{
                elems{
                  officeNumber
                  id
                }
                
                }
              }
            elems{
              clinicDoctorList{
                elems{
                  clinicDoctorAvailabilityList{
                    elems{
                      clinicOffice{
                        officeNumber
                      }
                      beginDate
                      endDate
                      clinicDoctor{
                        doctor{
                          entity{
                            person{
                              entity{lastName
                              firstName}
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
            }
          }
        """}
    requests_tool = TextRequestsWrapper()
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_clinic)
    return response


def to_do(dict):
    formatted_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    ft = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
    surname = dict.get('surname')
    print(dict)

    if surname is None:
        raise ValueError("Surname cannot be None")
    graphql_search_customer = {
        "operationName": "searchCustomer",
        "variables": {"searchStr": surname},  # No dollar sign here
        "query": """query searchCustomer($searchStr: String!){
                          searchCustomer(cond: "(it.person.entity.firstName+it.person.entity.lastName).$upper $like '%' + ${searchStr}.$upper + '%'")
                          @strExpr(string: $searchStr)
                          {
                            elems {
                              id
                            }
                          }
                        }"""
    }

    graphql_search_clinic = {
        "operationName": "",
        "variables": {},
        "query": """query {
              searchClinic{
                elems{
                  id
                  name
                }
              }
            }"""}
    requests_tool = TextRequestsWrapper()
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_clinic)
    response = json.loads(response)
    clinic_id = response['data']['searchClinic']['elems'][0]["id"]

    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_customer)
    response = json.loads(response)
    userid = response['data']['searchCustomer']['elems'][0]['id']
    graphql_search_clinic_table_for_customer = {
        "operationName": "",
        "variables": {"clinicId": clinic_id,
                      "dateFrom": formatted_time,
                      "dateTo": ft,
                      "customerId": userid},
                      "query": """query searchClinicTableForCustomer(
                      $clinicId: String!
                      $dateFrom: _DateTime!
                      $dateTo: _DateTime!
                      $customerId: String!
                    ) {
                      searchClinicTable(cond: "it.customer.entityId == ${customerId} && it.clinic.id == ${clinicId} && it.endDate >= ${dateFrom} && it.beginDate <= ${dateTo}")
                      @strExpr(strings:[$clinicId, $customerId],dateTimes:[$dateFrom,$dateTo])
                      {
                        elems {
                          endDate
                          beginDate
                          customer{
                            entity{
                              person{
                                entity{
                                  lastName
                                  firstName
                                }
                              }
                            }
                          }
                          clinicDoctor{
                            doctor{
                              entity{
                                doctorType{
                                  name
                                }
                                person{
                                  entity{
                                    lastName
                                    firstName
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }"""}
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_clinic_table_for_customer)
    return response


def i_feel_pain():

    graphql_search_doctors = {
        "operationName": "searchDoctors",
        "variables": {},
        "query": "query searchDoctors {\n  searchClinic {\n    elems {\n      clinicDoctorList {\n        elems {\n          clinic {\n            name\n          }\n          doctor {\n            entityId\n            entity {\n              person {\n                entityId\n                entity {\n                  lastName\n                }\n              }\n              doctorType {\n                name\n              }\n            }\n          }\n        }\n      }\n    }\n  }\n}\n"
    }
    requests_tool = TextRequestsWrapper()

    # Use the tool
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_doctors)
    print(response)
    return response

def appointment(message, state=GraphState, dict=None):
    question = state['question']
    surname = dict.get('surname')
    print(dict)

    if surname is None:
        raise ValueError("Surname cannot be None")

    print(surname)
    formatted_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    ft = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")

    # GraphQL request to find the customer by surname
    graphql_search_customer = {
        "operationName": "searchCustomer",
        "variables": {"searchStr": surname},
        "query": """query searchCustomer($searchStr: String!) {
                      searchCustomer(cond: "(it.person.entity.firstName+it.person.entity.lastName).$upper $like '%' + ${searchStr}.$upper + '%'")
                      @strExpr(string: $searchStr) {
                        elems {
                          id
                        }
                      }
                    }"""
                }

    requests_tool = TextRequestsWrapper()
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_customer)
    response = json.loads(response)
    customer_id = response['data']['searchCustomer']['elems'][0]['id']

    generarion = generate_appointment_data(message)
    print(type(generarion))

    # Initialize doctor_type
    doctor_type = None

    if generarion.get("name") and generarion.get("date"):
        date = generarion['date']
        doctor_name = generarion['name']
        print(date)

        graphql_search_doctorId_by_name = {
            "operationName": "",
            "variables": {"searchStr": doctor_name},
            "query": """query searchClinicDoctor($searchStr: String!) {
                          searchClinicDoctor(
                            cond: "(it.doctor.entity.person.entity.firstName+it.doctor.entity.person.entity.lastName).$upper $like '%' + ${searchStr}.$upper + '%'"
                          ) @strExpr(string: $searchStr) {
                            elems {
                              id
                            }
                          }
                        }"""}
        response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                      data=graphql_search_doctorId_by_name)
        response = json.loads(response)
        print(response)
        doctorId = response['data']['searchClinicDoctor']['elems'][0]['id']

    elif generarion.get("type") and generarion.get("date"):
        date = generarion['date']
        doctor_type = generarion['type']  # Use doctor_type here
        graphql_search_doctorId_by_type = {
            "operationName": "",
            "variables": {"searchStr": doctor_type},
            "query": """query searchClinicDoctor($searchStr: String!) {
                          searchClinicDoctor(
                            cond: "(it.doctor.entity.doctorType.name).$upper $like '%' + ${searchStr}.$upper + '%'"
                          ) @strExpr(string: $searchStr) {
                            elems {
                              id
                            }
                          }
                        }"""}

        response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                      data=graphql_search_doctorId_by_type)
        response = json.loads(response)
        print(response)
        doctorId = response['data']['searchClinicDoctor']['elems'][0]['id']

    else:
        return {"result": "Не хватает данных. Для записи напишите время и должность или фамилию врача"}

    search_clinic_doctor_availability = {
        "operationName": "",
        "variables": {"clinicDoctorId": doctorId, "dateFrom": formatted_time, "dateTo": ft},
        "query": """query searchClinicDoctorAvailability(
                      $clinicDoctorId: String!
                      $dateFrom: _DateTime!
                      $dateTo: _DateTime!
                    ) {
                      searchClinicDoctorAvailability(cond: "it.clinicDoctor.id == ${clinicDoctorId} && it.endDate >= ${dateFrom} && it.beginDate <= ${dateTo}")
                      @strExpr(string:$clinicDoctorId,dateTimes:[$dateFrom,$dateTo]) {
                        elems {
                          beginDate
                          endDate
                          clinicDoctor {
                            id
                          }
                          clinicOffice {
                            officeNumber
                            id
                            clinic {
                              id
                            }
                          }
                        }
                      }
                    }"""}
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=search_clinic_doctor_availability)
    response = json.loads(response)
    print(response)

    # Return the final clinic table with details
    return generate_clinic_table(customer_id, doctorId, response, date)



def generate_clinic_table(customer_id, doctor_id, availability, beginDate):
    date_for_mes = beginDate
    date_time = datetime.fromisoformat(beginDate)
    end_time = (date_time + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
    begin_time = date_time.strftime("%Y-%m-%dT%H:%M:%S")
    office_id = availability['data']['searchClinicDoctorAvailability']['elems'][0]['clinicOffice']['id']
    clinic_id = availability['data']['searchClinicDoctorAvailability']['elems'][0]['clinicOffice']['clinic']['id']

    create_clinic_table = {
        "operationName": "",
        "variables": {
            "clinicId": clinic_id,  # Assign actual ID
            "clinicDoctorId": doctor_id,
            "beginDate": begin_time,
            "endDate": end_time,
            "clinicOfficeId": office_id,  # Ensure actual ID if available
            "customerId": customer_id
                },
                "query": """
                   mutation createClinicTable(
                      $clinicId: ID!
                      $clinicDoctorId: ID!
                      $beginDate: _DateTime!
                      $endDate: _DateTime!
                      $clinicOfficeId: ID!
                      $customerId: String!
                    ) {
                      packet {
                        
                        getClinicDoctor(
                          id:"find: it.id == ${clinicDoctorId} && ${beginDate} < ${endDate} && it.clinicDoctorAvailabilityList{cond = it.clinicOffice.id == ${clinicOfficeId} && it.beginDate <= ${beginDate} && it.endDate>=${endDate}}.$exists"
                          failOnEmpty:true
                          lock:WAIT
                        ){
                          id
                        }
                        
                        getClinic(
                          id:"find: it.id == ${clinicId} && ${beginDate} < ${endDate} && !it.clinicTableList{cond = it.endDate >= ${beginDate} && it.beginDate<=${endDate} && (it.clinicDoctor.id == ${clinicDoctorId} || it.clinicOffice.id == ${clinicOfficeId} || it.customer.entityId == ${customerId})}.$exists"
                          failOnEmpty:true
                          lock:WAIT      
                        ){
                          id
                        }
                        
                        createClinicTable(input: {
                          clinic: $clinicId
                          clinicDoctor: $clinicDoctorId
                          clinicOffice: $clinicOfficeId
                          customer: {entityId: $customerId}
                          beginDate: $beginDate
                          endDate: $endDate
                          
                        }) {
                          id
                          customer{
                            entity{
                              person{
                                entity{
                                  lastName
                                  firstName
                                }
                              }
                            }
                          }
                          clinicOffice{
                            officeNumber
                          }
                          clinicDoctor{
                            doctor{
                              entity{
                                person{
                                  entity{
                                    lastName
                                  }
                                }
                              }
                            }
                          }
                          clinic{
                            name
                          }
                          beginDate
                          endDate
                        }
                      }
                    }"""}

    requests_tool = TextRequestsWrapper()
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql", data=create_clinic_table)
    response = json.loads(response)
    print(response)
    return {"result": f"Запись успешно создана! Вы записаны на время {date_for_mes} к доктору {response['data']['packet']}"}



def generate_appointment_data( message, state = GraphState, user_dict = {}):
    system = """
        Твоя задача получить данные используя информацию из {context}.
        {context} представляет из себя сообщение пользователя в текстовом формате.
        Найди данные о времени на которое можно записать пользователя, к какому врачу.
        Верни данные в формате json где date - время записи к врачу в формате %Y-%m-%dT%H:%M:%S,
        type - должность врача, например Хирург или Терапевт 
        name - фамилия врача.
        Перед отправкой файла перепроверь что он действительно в формате JSON, не используй внутри символ `
        """

    chat = GigaChat(
        model="GigaChat",
        credentials=creds,
        scope="GIGACHAT_API_PERS",  # "GIGACHAT_API_PERS",
        verify_ssl_certs=False,
        temperature=0.05
    )

    type_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "User question: {question}"),
        ]
    )

    chain = type_prompt | chat | StrOutputParser()
    generation = chain.invoke({"context": "", "question": message})

    generation = validate_json(generation)
    return json.loads(generation)

def validate_json(json):
    system = """
            Твоя задача валидировать JSON файл.
            Если файл не валидный то переделай его в правильный вид.
            Так же значения name и type должны быть на русском.
            В ответ отправляй только валидный JSON.
            """

    chat = GigaChat(
        model="GigaChat",
        credentials=creds,
        scope="GIGACHAT_API_PERS",  # "GIGACHAT_API_PERS",
        verify_ssl_certs=False,
        temperature=0.15
    )

    type_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "User question: {question}"),
        ]
    )

    chain = type_prompt | chat | StrOutputParser()
    generation = chain.invoke({"context": "", "question": json})
    print(generation)
    return generation


def generate_answer( message, context, context_type = "",state = GraphState, user_dict = {}):
    # Prompt
    system = """
    Твоя задача ответить на вопрос, используя информацию из {context}.
    {context} представляет из себя результат запроса к внешнему ресурсу в формате json.
    Приведи все данные в понятный человеку вид.
    clinicOffice - Кабинет в поликлинике
    Не забудь про знаки препинания.
    Отформатируй дату под формат РФ
    Проверь себя перед тем как отправить ответ.
    """

    if context_type == "i_feel_pain":
        system = """
            Твоя задача ответить на вопрос о выборе одного врача исходя из описанных симптомов, используя информацию из {context}.
            {context} представляет из себя результат запроса к внешнему ресурсу в формате json.
            Не забудь про знаки препинания
            """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "User question: {question}"),
        ]
    )


    giga = GigaChat(
    model="GigaChat",
    credentials=creds,
    scope="GIGACHAT_API_PERS",  # "GIGACHAT_API_PERS",
        verify_ssl_certs=False,

        temperature=0.1
    )

    # Chain
    chain = prompt | giga | StrOutputParser()

    # Run
    #context='{"data":{"searchClinic":{"elems":[{"clinicDoctorList":{"elems":[{"clinic":{"name":"Клиника N1"},"doctor":{"entityId":"7424408113957502977","entity":{"person":{"entityId":"7424406473279995905","entity":{"lastName":"Biryukov"}},"doctorType":{"name":"Терапевт"}}}},{"clinic":{"name":"Клиника N1"},"doctor":{"entityId":"7424408113957502979","entity":{"person":{"entityId":"7424406477574963202","entity":{"lastName":"Varenikov"}},"doctorType":{"name":"Хирург"}}}}]}}]}}}'


    """print("---GENERATE---")
    question = state["question"]
    context = state["context"]"""


    generation = chain.invoke({"context": context, "question": message})

    return {"context": context, "question": message, "generation": generation}


test = {"surname": "Панежа"}

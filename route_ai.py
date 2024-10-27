from imghdr import tests
from re import search
import time
from datetime import datetime, timedelta
from typing import Dict
from typing_extensions import TypedDict
import json
from langchain_community.utilities.requests import TextRequestsWrapper


class GraphState(TypedDict):
    args: Dict
    question: str
    generation: str
    context: str


def find_doctors(state = GraphState):
    question = state['question']

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
    #return {"question": question, "context": response}
    return response


def info_free_date(state = GraphState):
    question = state['question']

    formatted_time = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    ft = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")

    graphql_search_clinic_doctors_availability = {
        "operationName": "",
        "variables": {"dateFrom": f"{formatted_time}",
                      "dateTo": f"{ft}"},
        "query": """query searchClinicDoctorAvailability(
                  $dateFrom: _DateTime!
                  $dateTo: _DateTime!
                ) {
                  searchClinicDoctorAvailability(cond: "it.endDate >= ${dateFrom} && it.beginDate <= ${dateTo}")
                  @strExpr(dateTimes:[$dateFrom,$dateTo])
                  {
                    elems {
                        id
                      clinicDoctor{
                        doctor{
                          entity{
                            person{
                              entity{
                                lastName
                                firstName
                              }
                            }
                          }
                        }
                      }
                      beginDate
                      endDate
                      clinicOffice{
                        officeNumber
                        clinic{
                          name
                        }
                      }
                    }
                  }
                }"""
                }
    requests_tool = TextRequestsWrapper()

    # Use the tool
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_clinic_doctors_availability)
    response = json.loads(response)
    # return {"question": question, "context": response}
    return response




def verif(name='', lastname='', polis_num=''):
    graphql_search_person = {
        "operationName": "",
        "variables": {"searchStr": f"{lastname}"},
        "query": """query searchCustomer($searchStr: String!){
                      searchCustomer(cond: "(it.person.entity.firstName+it.person.entity.lastName).$upper $like '%' + ${searchStr}.$upper + '%'")
                      @strExpr(string: $searchStr)
                      {
                        elems {
                          person{
                            entity{
                              firstName
                              lastName
                            }
                          }
                          insurancePolicyNumber
                        }
                      }
                    }"""
    }

    requests_tool = TextRequestsWrapper()

    # Use the tool
    response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                  data=graphql_search_person)
    response = json.loads(response)

    if len(response['data']['searchCustomer']['elems']) != 0:
        name_db = response['data']['searchCustomer']['elems'][0]['person']['entity']['firstName']
        surname_db = response['data']['searchCustomer']['elems'][0]['person']['entity']['lastName']
        polis_db = response['data']['searchCustomer']['elems'][0]['insurancePolicyNumber']

        if name_db == name and surname_db == lastname and polis_db == polis_num:
            print("Юзер в базе")

    else:
        graphql_add_person = {
            "operationName": "createPerson",
            "variables": {"input": {"firstName": f"{name}", "lastName": f"{lastname}"}},
            "query": """mutation createPerson($input: _CreatePersonInput!) {
                  packet {
                    createPerson(input: $input) {
                      id
                      firstName
                      lastName
                    }
                  }
                }"""
        }
        response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                      data=graphql_add_person)
        response = json.loads(response)
        print(response['data']['packet']['createPerson']['id'])

        graphql_add_customer = {
            "operationName": "createCustomer",
            "variables": {"personId": f"{response['data']['packet']['createPerson']['id']}",
                          "insurancePolicyNumber": f"{polis_num}"},
            "query": """mutation createCustomer(
                      $personId:String!
                        $insurancePolicyNumber:String!
                      $phoneNumber:String 

                    ) {
                      packet {
                        createCustomer(input: {
                          person:{entityId:$personId}      
                          insurancePolicyNumber: $insurancePolicyNumber
                          phoneNumber: $phoneNumber

                        }) {
                          id
                          insurancePolicyNumber
                          person{
                            entity{
                              lastName
                              firstName
                            }
                          }
                        }
                      }
                    }
                    """}
        response = requests_tool.post(url="https://smapi.pv-api.sbc.space/ds-7430063538866552833/graphql",
                                      data=graphql_add_customer)
        print(response)

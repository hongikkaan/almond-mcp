"""Output field contracts, separate from tool roles and input instructions.

Most tools retain their JSON text transport. contentSchema describes the JSON
inside that text; it is metadata, not a promise that every optional field or
mode is present. Image and runtime tools expose the object directly.
"""
from copy import deepcopy

CONTRACTS = {'list_connections': {'type': 'object',
                      'properties': {'instructions': {'type': 'string',
                                                      'description': '연결 가능한 Rhino와 연결 선택 방법입니다.'},
                                     'targets': {'type': 'array',
                                                 'items': {'type': 'object',
                                                           'properties': {'connection_id': {'type': ['string',
                                                                                                     'null'],
                                                                                            'description': '연결 '
                                                                                                           'ID입니다. '
                                                                                                           '선택 후 '
                                                                                                           '일반 '
                                                                                                           '호출에서는 '
                                                                                                           '생략할 수 '
                                                                                                           '있습니다.'},
                                                                          'host_id': {'type': ['string', 'null'],
                                                                                      'description': 'Rhino 호스트 '
                                                                                                     'ID'},
                                                                          'state': {'type': 'string',
                                                                                    'description': '연결 상태입니다. '
                                                                                                   'ready에서 일반 '
                                                                                                   '작업을 수행하며 '
                                                                                                   'recovering/unconfirmed에서는 '
                                                                                                   '실행 결과부터 '
                                                                                                   '확인합니다.'},
                                                                          'reason': {'type': 'string',
                                                                                     'description': '상태 사유 또는 오류 '
                                                                                                    '내용. 없으면 빈 '
                                                                                                    '문자열'},
                                                                          'model_path': {'type': ['string',
                                                                                                  'null'],
                                                                                         'description': '저장된 모델의 '
                                                                                                        '경로'},
                                                                          'model_filename': {'type': ['string',
                                                                                                      'null'],
                                                                                             'description': '모델 '
                                                                                                            '파일명'},
                                                                          'slot': {'type': ['string', 'null'],
                                                                                   'description': '독립 연결 슬롯. 같은 '
                                                                                                  '폴더의 모델은 DB·산출물 '
                                                                                                  '루트를 공유'},
                                                                          'pid': {'type': ['integer', 'null'],
                                                                                  'description': 'Rhino 프로세스 ID'},
                                                                          'artifact_dir': {'type': ['string',
                                                                                                    'null'],
                                                                                           'description': '이 연결의 '
                                                                                                          '임시 작업 '
                                                                                                          '폴더입니다.'},
                                                                          'in_flight': {'type': 'boolean',
                                                                                        'description': '해당 연결에 '
                                                                                                       '호출이 진행 '
                                                                                                       '중인지 여부'}}},
                                                 'description': '연결 가능한 Rhino 문서 후보입니다.'},
                                     'connections': {'type': 'array',
                                                     'items': {'type': 'object',
                                                               'properties': {'connection_id': {'type': ['string',
                                                                                                         'null'],
                                                                                                'description': '연결 '
                                                                                                               'ID입니다. '
                                                                                                               '선택 '
                                                                                                               '후 '
                                                                                                               '일반 '
                                                                                                               '호출에서는 '
                                                                                                               '생략할 '
                                                                                                               '수 '
                                                                                                               '있습니다.'},
                                                                              'host_id': {'type': ['string',
                                                                                                   'null'],
                                                                                          'description': 'Rhino '
                                                                                                         '호스트 ID'},
                                                                              'state': {'type': 'string',
                                                                                        'description': '연결 상태입니다. '
                                                                                                       'ready에서 '
                                                                                                       '일반 작업을 '
                                                                                                       '수행하며 '
                                                                                                       'recovering/unconfirmed에서는 '
                                                                                                       '실행 결과부터 '
                                                                                                       '확인합니다.'},
                                                                              'reason': {'type': 'string',
                                                                                         'description': '상태 사유 또는 '
                                                                                                        '오류 내용. '
                                                                                                        '없으면 빈 '
                                                                                                        '문자열'},
                                                                              'model_path': {'type': ['string',
                                                                                                      'null'],
                                                                                             'description': '저장된 '
                                                                                                            '모델의 '
                                                                                                            '경로'},
                                                                              'model_filename': {'type': ['string',
                                                                                                          'null'],
                                                                                                 'description': '모델 '
                                                                                                                '파일명'},
                                                                              'slot': {'type': ['string', 'null'],
                                                                                       'description': '독립 연결 슬롯. '
                                                                                                      '같은 폴더의 모델은 '
                                                                                                      'DB·산출물 루트를 '
                                                                                                      '공유'},
                                                                              'pid': {'type': ['integer', 'null'],
                                                                                      'description': 'Rhino 프로세스 '
                                                                                                     'ID'},
                                                                              'artifact_dir': {'type': ['string',
                                                                                                        'null'],
                                                                                               'description': '이 '
                                                                                                              '연결의 '
                                                                                                              '임시 '
                                                                                                              '작업 '
                                                                                                              '폴더입니다.'},
                                                                              'in_flight': {'type': 'boolean',
                                                                                            'description': '해당 '
                                                                                                           '연결에 '
                                                                                                           '호출이 '
                                                                                                           '진행 '
                                                                                                           '중인지 '
                                                                                                           '여부'}}},
                                                     'description': '현재 유지 중인 연결입니다.'},
                                     'starts': {'type': 'array',
                                                'items': {'type': 'object',
                                                          'properties': {'request_id': {'type': 'string',
                                                                                        'description': '재사용할 시작 '
                                                                                                       '요청 '
                                                                                                       'ID입니다.'},
                                                                         'state': {'type': 'string',
                                                                                   'description': '시작 요청의 상태입니다.'},
                                                                         'model_path': {'type': 'string',
                                                                                        'description': '열 모델의 절대 '
                                                                                                       '경로입니다.'},
                                                                         'connection_id': {'type': ['string',
                                                                                                    'null'],
                                                                                           'description': '연결된 '
                                                                                                          '경우의 '
                                                                                                          'ID입니다.'},
                                                                         'reason': {'type': 'string',
                                                                                    'description': '현재 상태의 '
                                                                                                   '사유입니다.'}}},
                                                'description': 'Rhino 시작 요청과 진행 상태입니다.'},
                                     'selected_connection_id': {'type': ['string', 'null'],
                                                                'description': '이후 호출에서 사용하는 연결 ID입니다. 선택된 연결이 '
                                                                               '없으면 null입니다.'},
                                     'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                     'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                     'next_step_guide': {'type': 'string',
                                                         'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                        '반환합니다.'}}},
 'connect': {'type': 'object',
             'properties': {'connection_id': {'type': ['string', 'null'],
                                              'description': '연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.'},
                            'host_id': {'type': ['string', 'null'], 'description': 'Rhino 호스트 ID'},
                            'state': {'type': 'string',
                                      'description': '연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 '
                                                     '결과부터 확인합니다.'},
                            'reason': {'type': 'string', 'description': '상태 사유 또는 오류 내용. 없으면 빈 문자열'},
                            'model_path': {'type': ['string', 'null'], 'description': '저장된 모델의 경로'},
                            'model_filename': {'type': ['string', 'null'], 'description': '모델 파일명'},
                            'slot': {'type': ['string', 'null'],
                                     'description': '독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유'},
                            'pid': {'type': ['integer', 'null'], 'description': 'Rhino 프로세스 ID'},
                            'artifact_dir': {'type': ['string', 'null'], 'description': '이 연결의 임시 작업 폴더입니다.'},
                            'in_flight': {'type': 'boolean', 'description': '해당 연결에 호출이 진행 중인지 여부'},
                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                            'next_step_guide': {'type': 'string',
                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'start_session': {'type': 'object',
                   'properties': {'connection_id': {'type': ['string', 'null'],
                                                    'description': '연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.'},
                                  'host_id': {'type': ['string', 'null'], 'description': 'Rhino 호스트 ID'},
                                  'state': {'type': 'string',
                                            'description': '연결 상태입니다. ready에서 일반 작업을 수행하며 '
                                                           'recovering/unconfirmed에서는 실행 결과부터 확인합니다.'},
                                  'reason': {'type': 'string', 'description': '상태 사유 또는 오류 내용. 없으면 빈 문자열'},
                                  'model_path': {'type': ['string', 'null'], 'description': '저장된 모델의 경로'},
                                  'model_filename': {'type': ['string', 'null'], 'description': '모델 파일명'},
                                  'slot': {'type': ['string', 'null'],
                                           'description': '독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유'},
                                  'pid': {'type': ['integer', 'null'], 'description': 'Rhino 프로세스 ID'},
                                  'artifact_dir': {'type': ['string', 'null'],
                                                   'description': '이 연결의 임시 작업 폴더입니다.'},
                                  'in_flight': {'type': 'boolean', 'description': '해당 연결에 호출이 진행 중인지 여부'},
                                  'request_id': {'type': 'string',
                                                 'description': '동일 시작 시도에 재사용. 대기·실패 상태는 '
                                                                'list_connections.starts에서 확인'},
                                  'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                  'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                  'next_step_guide': {'type': 'string',
                                                      'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                     '반환합니다.'}}},
 'disconnect': {'type': 'object',
                'properties': {'connection_id': {'type': 'string', 'description': '해제한 연결 ID입니다.'},
                               'pid': {'type': ['integer', 'null'],
                                       'description': '해제한 연결의 Rhino 프로세스 ID입니다. 종료할 창을 식별할 때 model_path와 함께 확인합니다.'},
                               'model_path': {'type': ['string', 'null'],
                                              'description': '해제한 연결에 저장된 모델 경로입니다. 저장·종료 전에 현재 문서 경로와 일치하는지 확인합니다.'},
                               'worker_closed': {'type': 'boolean', 'description': 'worker가 종료됐는지 여부'},
                               'rhino_closed': {'type': 'boolean',
                                                'description': 'Rhino가 닫혔는지 여부. disconnect는 false'},
                               'released': {'type': 'boolean', 'description': 'Rhino에서 연결 해제를 확인했는지 나타냅니다.'},
                               'reason': {'type': 'string', 'description': '해제 결과 또는 남아 있는 잠금의 사유입니다.'},
                               'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                               'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                               'next_step_guide': {'type': 'string',
                                                   'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'project_info': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                 'project': {'type': 'object',
                                             'properties': {'project_root': {'type': 'string',
                                                                             'description': '프로젝트의 절대 경로입니다. 프로젝트 '
                                                                                            '파일 도구의 상대 경로 기준입니다.'},
                                                            'file_name': {'type': ['string', 'null'],
                                                                          'description': '파일명입니다.'},
                                                            'file_path': {'type': ['string', 'null'],
                                                                          'description': '파일 경로입니다.'},
                                                            'is_bound_document': {'type': 'boolean',
                                                                                  'description': '현재 Rhino 문서가 이 '
                                                                                                 '연결의 모델과 일치하는지 '
                                                                                                 '나타냅니다.'},
                                                            'files': {'type': 'array',
                                                                      'items': {'type': 'object',
                                                                                'properties': {'project_file_id': {'type': 'string',
                                                                                                                   'description': '등록 '
                                                                                                                                  '파일 '
                                                                                                                                  'ID입니다. '
                                                                                                                                  'Scene의 '
                                                                                                                                  '파일 '
                                                                                                                                  '연결에 '
                                                                                                                                  '사용합니다.'},
                                                                                               'file_name': {'type': 'string',
                                                                                                             'description': '파일명입니다.'}}},
                                                                      'description': '프로젝트에 등록한 Rhino 파일 목록입니다.'},
                                                            'files_page': {'type': 'object',
                                                                           'properties': {'total': {'type': 'integer',
                                                                                                    'description': '조회 '
                                                                                                                   '조건에 '
                                                                                                                   '맞는 '
                                                                                                                   '전체 '
                                                                                                                   '항목 '
                                                                                                                   '수입니다.'},
                                                                                          'limit': {'type': 'integer',
                                                                                                    'description': '이번 '
                                                                                                                   '응답의 '
                                                                                                                   '최대 '
                                                                                                                   '항목 '
                                                                                                                   '수입니다.'},
                                                                                          'offset': {'type': 'integer',
                                                                                                     'description': '이번 '
                                                                                                                    '페이지의 '
                                                                                                                    '시작 '
                                                                                                                    '위치입니다.'},
                                                                                          'truncated': {'type': 'boolean',
                                                                                                        'description': 'true면 '
                                                                                                                       '같은 '
                                                                                                                       '조건에서 '
                                                                                                                       'files_offset을 '
                                                                                                                       'offset+limit으로 '
                                                                                                                       '이어감'}},
                                                                           'description': '등록 파일 목록의 페이지 정보입니다.'}},
                                             'description': '현재 연결 문서와 프로젝트 정보입니다.'},
                                 'locations': {'type': 'object',
                                               'properties': {'plan_id': {'type': 'string',
                                                                          'description': '현재 작업 대상으로 선택한 Plan '
                                                                                         'ID입니다.'},
                                                              'step_id': {'type': 'string',
                                                                          'description': 'Step ID입니다.'},
                                                              'artifact_dir': {'description': '현재 연결에서 사용할 '
                                                                                              'Plan·Loop 산출물 '
                                                                                              '폴더입니다. 선택 전에는 '
                                                                                              'null입니다.',
                                                                               'type': ['string', 'null']},
                                                              'database': {'type': 'string',
                                                                           'description': '공유 데이터베이스 경로입니다.'}},
                                               'description': '현재 연결의 작업 공간과 공유 데이터베이스 위치입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'get_policy': {'type': 'object',
                'properties': {'status': {'type': 'string',
                                          'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                               'guide_version': {'type': 'string', 'description': '지침 버전을 비교하는 해시입니다.'},
                               'text': {'type': 'string', 'description': '선택한 policy의 지침 본문입니다.'},
                               'source_refs': {'type': 'array',
                                               'items': {'type': 'object',
                                                         'properties': {'path': {'type': 'string',
                                                                                 'description': '안내문 출처 경로'},
                                                                        'sha256': {'type': 'string',
                                                                                   'description': '파일 해시.'}}},
                                               'description': '선택한 지침의 출처 파일과 해시입니다.'},
                               'tools': {'type': 'array',
                                         'items': {'type': 'string'},
                                         'description': '사용할 수 있는 도구 이름 목록입니다.'},
                               'selected_policy': {'type': 'string', 'description': '선택한 policy 이름입니다.'},
                               'available_policies': {'type': 'object',
                                                      'additionalProperties': {'type': 'string'},
                                                      'description': '선택 가능한 policy 이름과 설명입니다.'},
                               'policy': {'type': 'object', 'description': 'metadata 지침입니다.'},
                               'scripting_skill': {'description': 'Rhino 스크립팅 지침입니다.', 'type': 'object'},
                               'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                               'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                               'next_step_guide': {'type': 'string',
                                                   'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'create_phase': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                 'phase': {'type': 'object',
                                           'properties': {'phase_id': {'type': 'string',
                                                                       'description': '생성한 Phase ID입니다. Plan의 소속 '
                                                                                      '지정이나 Phase 조회에 사용합니다.'}},
                                           'description': '생성한 Phase입니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'create_plan': {'type': 'object',
                 'properties': {'status': {'type': 'string',
                                           'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                'plan': {'type': 'object',
                                         'properties': {'plan_id': {'type': 'string',
                                                                    'description': '생성한 Plan ID입니다. 상세 조회·회차 '
                                                                                   '시작·작업 공간 선택에 사용합니다.'},
                                                        'loop_no': {'type': 'integer',
                                                                    'description': '현재 Loop 번호입니다. 0은 회차 시작 '
                                                                                   '전입니다.'},
                                                        'revision': {'type': 'integer',
                                                                     'description': '저장 리비전입니다. 수정 시 loop_no와 함께 '
                                                                                    'expected_revision에 사용할 수 '
                                                                                    '있습니다.'}},
                                         'description': '생성한 Plan입니다.'},
                                'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                'next_step_guide': {'type': 'string',
                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'execute_looping': {'type': 'object',
                     'properties': {'status': {'type': 'string',
                                               'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                    'plan_id': {'type': 'string', 'description': 'Plan ID'},
                                    'loop_no': {'type': 'integer', 'description': 'Loop 회차 번호'},
                                    'next_step_id': {'type': ['string', 'null'],
                                                     'description': '아직 완료되지 않은 첫 Step의 ID입니다. 없으면 null입니다.'},
                                    'previous_loop': {'type': ['object', 'null'],
                                                      'description': '이전 회차의 번호와 Step 기록입니다.'},
                                    'step_id': {'type': 'string', 'description': '선택한 Step ID입니다.'},
                                    'plan_artifact_dir': {'type': 'string', 'description': 'Plan 산출물 폴더'},
                                    'artifact_dir': {'type': ['string', 'null'], 'description': '작업 산출물 폴더'},
                                    'revision': {'type': 'integer', 'description': '현재 Plan·Loop의 저장 리비전입니다.'},
                                    'title': {'type': 'string', 'description': '저장된 제목'},
                                    'goal': {'type': 'string', 'description': '저장된 목표'},
                                    'plan_status': {'type': 'string',
                                                    'description': 'Plan의 업무 상태입니다. 회차 시작만으로 변경되지는 않습니다.'},
                                    'feedback': {'type': 'string', 'description': '저장된 피드백'},
                                    'steps': {'type': 'array',
                                              'items': {'type': 'object',
                                                        'properties': {'step_id': {'type': 'string',
                                                                                   'description': 'Step ID입니다.'},
                                                                       'name': {'type': 'string',
                                                                                'description': '저장된 이름'},
                                                                       'status': {'type': 'string',
                                                                                  'description': '업무 상태입니다. '
                                                                                                 'pending, '
                                                                                                 'running, '
                                                                                                 'paused, '
                                                                                                 'completed, '
                                                                                                 'failed, blocked '
                                                                                                 '중 하나입니다.'}}},
                                              'description': '이 회차의 Step과 작업 기록입니다.'},
                                    'policy_reminder': {'type': 'string',
                                                        'description': '이번 작업과 결과 보고에 적용할 지침입니다.'},
                                    'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                    'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                    'next_step_guide': {'type': 'string',
                                                        'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                       '반환합니다.'}}},
 'get_phase_plan_step': {'type': 'object',
                         'properties': {'id': {'type': 'string', 'description': '조회한 Phase·Plan·Step의 ID입니다.'},
                                        'type': {'type': 'string',
                                                 'enum': ['phase', 'plan', 'step'],
                                                 'description': '조회한 유형입니다.'},
                                        'name': {'type': 'string', 'description': '조회한 항목의 이름입니다.'},
                                        'status': {'type': 'string',
                                                   'description': '업무 상태입니다. pending, running, paused, completed, '
                                                                  'failed, blocked 중 하나이며 조회 실패는 error입니다.'},
                                        'plan_id': {'type': 'string', 'description': 'Plan·Step이 속한 Plan ID입니다.'},
                                        'loop_no': {'type': 'integer',
                                                    'description': 'Loop 번호입니다. 0은 회차 시작 전입니다.'},
                                        'revision': {'type': 'integer', 'description': '이 회차에 저장된 리비전 번호입니다.'},
                                        'read_only': {'type': 'boolean',
                                                      'description': '과거 회차·리비전이면 true입니다. 수정하려면 현재 상태를 다시 '
                                                                     '조회합니다.'},
                                        'phase': {'type': 'object',
                                                  'description': 'include_details=true인 Phase의 상세 내용입니다.',
                                                  'properties': {'description': {'type': 'string',
                                                                                 'description': 'Phase 설명입니다.'},
                                                                 'file_name': {'type': 'array',
                                                                               'items': {'type': 'string'},
                                                                               'description': 'Phase가 속한 Rhino '
                                                                                              '파일명 목록입니다.'},
                                                                 'depends_on': {'type': 'array',
                                                                                'items': {'type': 'string'},
                                                                                'description': '의존하는 Phase ID '
                                                                                               '목록입니다.'},
                                                                 'previous_id': {'type': ['string', 'null'],
                                                                                 'description': '이전 Phase ID입니다.'},
                                                                 'plan_titles': {'type': 'array',
                                                                                 'items': {'type': 'string'},
                                                                                 'description': '소속 Plan의 '
                                                                                                '제목입니다.'}}},
                                        'plan': {'type': 'object',
                                                 'description': 'include_details=true인 Plan의 목표·대상·관계·산출물·Step '
                                                                '요약입니다.',
                                                 'properties': {'goal': {'type': 'string',
                                                                         'description': '작업 목표입니다.'},
                                                                'scope': {'type': 'string',
                                                                          'description': 'Step 템플릿입니다.'},
                                                                'holon_ids': {'type': 'array',
                                                                              'items': {'type': 'string'},
                                                                              'description': 'Plan에 지정한 Holon '
                                                                                             'ID입니다.'},
                                                                'steps': {'type': 'array',
                                                                          'items': {'type': 'object',
                                                                                    'properties': {'step_id': {'type': 'string',
                                                                                                               'description': 'Step '
                                                                                                                              'ID입니다.'},
                                                                                                   'step_type': {'type': 'string',
                                                                                                                 'description': '템플릿 '
                                                                                                                                '역할입니다.'},
                                                                                                   'name': {'type': 'string',
                                                                                                            'description': 'Step '
                                                                                                                           '이름입니다.'},
                                                                                                   'status': {'type': 'string',
                                                                                                              'description': 'Step의 '
                                                                                                                             '업무 '
                                                                                                                             '상태입니다.'},
                                                                                                   'loop_no': {'type': 'integer',
                                                                                                               'description': '해당 '
                                                                                                                              '회차 '
                                                                                                                              '번호입니다.'}}},
                                                                          'description': 'Step 요약 목록입니다.'},
                                                                'artifact_refs': {'type': 'array',
                                                                                  'items': {'type': 'string'},
                                                                                  'description': 'Plan 산출물의 '
                                                                                                 '참조입니다.'},
                                                                'artifact_dir': {'type': 'string',
                                                                                 'description': 'Plan 산출물 루트입니다.'},
                                                                'loop_artifact_dir': {'type': 'string',
                                                                                      'description': '선택한 회차의 산출물 '
                                                                                                     '폴더입니다.'},
                                                                'phase': {'type': ['object', 'null'],
                                                                          'description': '소속 Phase의 ID와 이름입니다.',
                                                                          'properties': {'phase_id': {'type': 'string',
                                                                                                      'description': 'Phase '
                                                                                                                     'ID입니다.'},
                                                                                         'name': {'type': 'string',
                                                                                                  'description': 'Phase '
                                                                                                                 '이름입니다.'}}},
                                                                'scene_ids': {'type': 'array',
                                                                              'description': '작업 맥락으로 지정한 Scene '
                                                                                             'ID입니다.',
                                                                              'items': {'type': 'string'}},
                                                                'depends_on': {'type': 'array',
                                                                               'description': '의존하는 Plan ID입니다.',
                                                                               'items': {'type': 'string'}},
                                                                'previous_id': {'type': ['string', 'null'],
                                                                                'description': '이전 Plan ID입니다.'},
                                                                'parent_plan': {'type': 'array',
                                                                                'description': '상위 Plan ID입니다.',
                                                                                'items': {'type': 'string'}},
                                                                'child_plan': {'type': 'array',
                                                                               'description': '하위 Plan ID입니다.',
                                                                               'items': {'type': 'string'}},
                                                                'feedback': {'type': 'string',
                                                                             'description': '현재 Loop에 기록한 '
                                                                                            '피드백입니다.'},
                                                                'created_at': {'type': 'string',
                                                                               'description': '생성 시각입니다. 한국 시간 '
                                                                                              'YYYY-MM-DD-HH:MM '
                                                                                              '형식입니다.'},
                                                                'updated_at': {'type': 'string',
                                                                               'description': '수정 시각입니다. 한국 시간 '
                                                                                              'YYYY-MM-DD-HH:MM '
                                                                                              '형식입니다.'}}},
                                        'step': {'type': 'object',
                                                 'description': 'include_details=true인 Step의 상세 내용입니다.',
                                                 'properties': {'step_type': {'type': 'string',
                                                                              'description': '템플릿에서 정한 Step '
                                                                                             '역할입니다.'},
                                                                'input_refs': {'type': 'array',
                                                                               'items': {'type': 'string'},
                                                                               'description': '작업에 사용한 입력 근거입니다.'},
                                                                'output_refs': {'type': 'array',
                                                                                'items': {'type': 'string'},
                                                                                'description': '작업 결과의 근거입니다.'}}},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'list_phases': {'type': 'object',
                 'properties': {'status': {'type': 'string',
                                           'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                'phases': {'type': 'array',
                                           'items': {'type': 'object',
                                                     'properties': {'phase_id': {'type': 'string',
                                                                                 'description': 'Phase ID입니다.'},
                                                                    'name': {'type': 'string',
                                                                             'description': 'Phase 이름입니다.'},
                                                                    'status': {'type': 'string',
                                                                               'description': 'Phase의 업무 상태입니다.'},
                                                                    'plan_count': {'type': 'integer',
                                                                                   'description': '소속 Plan 수입니다.'},
                                                                    'depends_on': {'type': 'array',
                                                                                   'items': {'type': 'string'},
                                                                                   'description': '의존하는 Phase '
                                                                                                  'ID입니다.'},
                                                                    'previous_id': {'type': ['string', 'null'],
                                                                                    'description': '이전 Phase '
                                                                                                   'ID입니다.'},
                                                                    'file_name': {'type': 'array',
                                                                                  'items': {'type': 'string'},
                                                                                  'description': 'scope 그룹에서 반환하는 '
                                                                                                 'Rhino 파일명 '
                                                                                                 '목록입니다.'}}},
                                           'description': 'Phase 목록입니다.'},
                                'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                'truncated': {'type': 'boolean', 'description': 'limit 때문에 목록 일부만 반환했는지 나타냅니다.'},
                                'next_step_guide': {'type': 'string',
                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'},
                                'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'list_plan_revisions': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'plan_id': {'type': 'string',
                                                    'description': '각 행의 loop_no/revision과 함께 '
                                                                   'get_phase_plan_step에 사용'},
                                        'revisions': {'type': 'array',
                                                      'items': {'type': 'object',
                                                                'properties': {'loop_no': {'type': 'integer',
                                                                                           'description': '기록된 '
                                                                                                          'Loop '
                                                                                                          '번호입니다.'},
                                                                               'revision': {'type': 'integer',
                                                                                            'description': '저장 '
                                                                                                           '리비전 '
                                                                                                           '번호입니다.'},
                                                                               'operation': {'type': 'string',
                                                                                             'description': '이 '
                                                                                                            '기록을 '
                                                                                                            '만든 '
                                                                                                            '변경 '
                                                                                                            '작업입니다.'},
                                                                               'step_id': {'type': ['string',
                                                                                                    'null'],
                                                                                           'description': '변경한 '
                                                                                                          'Step '
                                                                                                          'ID입니다. '
                                                                                                          'Plan '
                                                                                                          '전체 '
                                                                                                          '변경이면 '
                                                                                                          'null입니다.'},
                                                                               'created_at': {'type': 'string',
                                                                                              'description': 'audit '
                                                                                                             '그룹에서 '
                                                                                                             '반환하는 '
                                                                                                             '저장 '
                                                                                                             '시각입니다.'}}},
                                                      'description': '저장 리비전 목록입니다.'},
                                        'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                        'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                        'truncated': {'type': 'boolean',
                                                      'description': 'limit 때문에 최신 리비전 일부만 반환했는지 나타냅니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'list_plans': {'type': 'object',
                'properties': {'status': {'type': 'string',
                                          'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                               'plans': {'type': 'array',
                                         'items': {'type': 'object',
                                                   'properties': {'plan_id': {'type': 'string',
                                                                              'description': 'Plan ID입니다.'},
                                                                  'title': {'type': 'string',
                                                                            'description': 'Plan 제목입니다.'},
                                                                  'scope': {'type': 'string',
                                                                            'description': 'Step 템플릿 키입니다.'},
                                                                  'status': {'type': 'string',
                                                                             'description': 'Plan의 업무 상태입니다.'},
                                                                  'loop_no': {'type': 'integer',
                                                                              'description': '현재 Loop 번호입니다.'},
                                                                  'revision': {'type': 'integer',
                                                                               'description': '현재 리비전입니다.'}}},
                                         'description': 'Plan 목록입니다.'},
                               'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                               'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                               'truncated': {'type': 'boolean', 'description': 'limit 때문에 목록 일부만 반환했는지 나타냅니다.'},
                               'next_step_guide': {'type': 'string',
                                                   'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'},
                               'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                               'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'rename_artifact_folder': {'type': 'object',
                            'properties': {'status': {'type': 'string',
                                                      'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                     '확인합니다.'},
                                           'artifact_dir': {'type': ['string', 'null'],
                                                            'description': '변경 후 산출물 폴더 경로입니다.'},
                                           'previous_artifact_dir': {'type': 'string',
                                                                     'description': '변경 전 폴더 경로입니다. 실제 변경이 있을 때 '
                                                                                    '반환합니다.'},
                                           'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                           'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                           'next_step_guide': {'type': 'string',
                                                               'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                              '반환합니다.'}}},
 'set_working_plan': {'type': 'object',
                      'properties': {'status': {'type': 'string',
                                                'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                     'plan_id': {'type': 'string', 'description': 'Plan ID'},
                                     'step_id': {'type': 'string', 'description': '선택한 Step. Step 미선택이면 빈 문자열'},
                                     'loop_no': {'type': 'integer', 'description': 'Loop 회차 번호'},
                                     'revision': {'type': 'integer', 'description': '작업 공간 설정 후의 저장 리비전입니다.'},
                                     'artifact_dir': {'type': ['string', 'null'],
                                                      'description': '현재 연결의 산출물 폴더입니다. execute_project_python의 '
                                                                     '작업 디렉터리로 사용합니다.'},
                                     'plan_artifact_dir': {'type': 'string',
                                                           'description': 'Plan 산출물 루트입니다. Loop 시작 전에는 이 폴더를 '
                                                                          '사용합니다.'},
                                     'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                     'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                     'next_step_guide': {'type': 'string',
                                                         'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                        '반환합니다.'}}},
 'update_phase': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                 'changed': {'type': 'boolean',
                                             'description': '실제 저장 변경 여부. status=success여도 false일 수 있음'},
                                 'phase': {'type': 'object',
                                           'properties': {'phase_id': {'type': 'string',
                                                                       'description': 'Phase ID'},
                                                          'status': {'type': 'string',
                                                                     'description': '업무 상태입니다. pending, running, '
                                                                                    'paused, completed, failed, '
                                                                                    'blocked 중 하나입니다.'}},
                                           'description': '수정한 Phase의 확인 정보입니다.'},
                                 'issues': {'type': 'array',
                                            'items': {'type': 'object',
                                                      'properties': {'field': {'type': 'string',
                                                                               'description': '문제가 있는 입력 필드입니다.'},
                                                                     'operation': {'type': 'string',
                                                                                   'description': 'add 또는 '
                                                                                                  'remove입니다.'},
                                                                     'index': {'type': 'integer',
                                                                               'description': '해당 배열에서의 0부터 시작하는 '
                                                                                              '위치입니다.'},
                                                                     'value': {'description': '요청한 값입니다.'},
                                                                     'reason': {'type': 'string',
                                                                                'description': '건너뛴 이유입니다.'}}},
                                            'description': '적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'update_plan': {'type': 'object',
                 'properties': {'status': {'type': 'string',
                                           'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                'changed': {'type': 'boolean',
                                            'description': '실제 변경일 때만 리비전 하나 생성. success여도 false일 수 있음'},
                                'plan': {'type': 'object',
                                         'properties': {'plan_id': {'type': 'string', 'description': 'Plan ID'},
                                                        'status': {'type': 'string',
                                                                   'description': '업무 상태입니다. pending, running, '
                                                                                  'paused, completed, failed, '
                                                                                  'blocked 중 하나입니다.'},
                                                        'loop_no': {'type': 'integer',
                                                                    'description': 'Loop 회차 번호'},
                                                        'revision': {'type': 'integer',
                                                                     'description': '다음 수정의 선택적 expected_revision '
                                                                                    '값. loop_no도 함께 사용'}},
                                         'description': '수정한 Plan의 확인 정보입니다.'},
                                'issues': {'type': 'array',
                                           'items': {'type': 'object',
                                                     'properties': {'field': {'type': 'string',
                                                                              'description': '문제가 있는 입력 필드입니다.'},
                                                                    'operation': {'type': 'string',
                                                                                  'description': 'add 또는 '
                                                                                                 'remove입니다.'},
                                                                    'index': {'type': 'integer',
                                                                              'description': '해당 배열에서의 0부터 시작하는 '
                                                                                             '위치입니다.'},
                                                                    'value': {'description': '요청한 값입니다.'},
                                                                    'reason': {'type': 'string',
                                                                               'description': '건너뛴 이유입니다.'}}},
                                           'description': '적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.'},
                                'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                'next_step_guide': {'type': 'string',
                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'update_step': {'type': 'object',
                 'properties': {'status': {'type': 'string',
                                           'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                'changed': {'type': 'boolean',
                                            'description': '실제 변경일 때만 Plan 리비전 하나 생성. success여도 false일 수 있음'},
                                'plan': {'type': 'object',
                                         'properties': {'plan_id': {'type': 'string', 'description': 'Plan ID'},
                                                        'status': {'type': 'string',
                                                                   'description': '업무 상태입니다. pending, running, '
                                                                                  'paused, completed, failed, '
                                                                                  'blocked 중 하나입니다.'},
                                                        'loop_no': {'type': 'integer',
                                                                    'description': 'Loop 번호입니다. 0은 회차 시작 전입니다.'},
                                                        'revision': {'type': 'integer',
                                                                     'description': '다음 수정의 선택적 expected_revision '
                                                                                    '값. loop_no도 함께 사용'}},
                                         'description': '수정한 Step이 속한 Plan의 확인 정보입니다.'},
                                'issues': {'type': 'array',
                                           'items': {'type': 'object',
                                                     'properties': {'field': {'type': 'string',
                                                                              'description': '문제가 있는 입력 필드입니다.'},
                                                                    'operation': {'type': 'string',
                                                                                  'description': 'add 또는 '
                                                                                                 'remove입니다.'},
                                                                    'index': {'type': 'integer',
                                                                              'description': '해당 배열에서의 0부터 시작하는 '
                                                                                             '위치입니다.'},
                                                                    'value': {'description': '요청한 값입니다.'},
                                                                    'reason': {'type': 'string',
                                                                               'description': '건너뛴 이유입니다.'}}},
                                           'description': '적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.'},
                                'step': {'type': 'object',
                                         'properties': {'step_id': {'type': 'string', 'description': 'Step ID'},
                                                        'status': {'type': 'string',
                                                                   'description': '업무 상태입니다. pending, running, '
                                                                                  'paused, completed, failed, '
                                                                                  'blocked 중 하나입니다.'},
                                                        'loop_no': {'type': 'integer',
                                                                    'description': 'Loop 번호입니다. 0은 회차 시작 전입니다.'}},
                                         'description': '수정한 Step의 확인 정보입니다.'},
                                'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                'next_step_guide': {'type': 'string',
                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'analyze_block_reculviely': {'type': 'object',
                              'properties': {'status': {'type': 'string',
                                                        'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                       '확인합니다.'},
                                             'mode': {'type': 'string', 'description': '선택한 분석 모드입니다.'},
                                             'document': {'type': 'object',
                                                          'properties': {'units': {'type': 'string',
                                                                                   'description': '문서의 길이 단위입니다.'},
                                                                         'absolute_tolerance': {'type': 'number',
                                                                                                'description': '문서 '
                                                                                                               '길이 '
                                                                                                               '단위의 '
                                                                                                               '절대 '
                                                                                                               '허용오차입니다.'}},
                                                          'description': '관찰한 문서 정보입니다.'},
                                             'data': {'type': 'object',
                                                      'properties': {'records': {'type': 'array',
                                                                                 'items': {'type': 'object',
                                                                                           'properties': {'kind': {'type': 'string',
                                                                                                                   'description': '항목의 '
                                                                                                                                  '종류입니다.'},
                                                                                                          'id': {'type': 'string',
                                                                                                                 'description': '항목 '
                                                                                                                                'ID입니다.'},
                                                                                                          'type': {'type': 'string',
                                                                                                                   'description': '객체 '
                                                                                                                                  '유형입니다.'},
                                                                                                          'path': {'type': 'array',
                                                                                                                   'items': {'type': 'string'},
                                                                                                                   'description': '중첩 '
                                                                                                                                  '블록의 '
                                                                                                                                  '배치 '
                                                                                                                                  '경로입니다. '
                                                                                                                                  'resolve-block의 '
                                                                                                                                  'options.path로 '
                                                                                                                                  '사용할 '
                                                                                                                                  '수 '
                                                                                                                                  '있습니다.'},
                                                                                                          'definition': {'type': 'string',
                                                                                                                         'description': '블록 '
                                                                                                                                        '정의 '
                                                                                                                                        '이름입니다.'}}},
                                                                                 'description': '블록 배치 또는 정의의 분석 '
                                                                                                '항목입니다.'},
                                                                     'items': {'type': 'integer',
                                                                               'description': '반환한 분석 항목 수입니다.'},
                                                                     'truncated': {'type': 'boolean',
                                                                                   'description': '조회 한도 때문에 분석 '
                                                                                                  '항목 일부가 생략됐는지 '
                                                                                                  '나타냅니다.'}},
                                                      'description': '선택한 블록 분석 모드의 결과입니다.'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'get_objects': {'type': 'object',
                 'properties': {'status': {'type': 'string',
                                           'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                'scope': {'type': 'string', 'description': '이번 조회에서 관찰한 객체 범위입니다.'},
                                'objects': {'type': 'array',
                                            'items': {'type': 'object',
                                                      'properties': {'id': {'type': 'string',
                                                                            'description': '관찰한 객체 ID입니다.'},
                                                                     'geometry_crc': {'type': 'number',
                                                                                      'description': '관찰한 형상 '
                                                                                                     '버전입니다. 면 '
                                                                                                     '편집이나 다음 면 '
                                                                                                     '페이지 조회에 '
                                                                                                     '사용합니다.'},
                                                                     'face_count': {'type': 'integer',
                                                                                    'description': '객체의 전체 면 '
                                                                                                   '수입니다.'},
                                                                     'faces': {'type': 'array',
                                                                               'items': {'type': 'object',
                                                                                         'properties': {'face_index': {'type': 'number',
                                                                                                                       'description': '이 '
                                                                                                                                      'id·CRC와 '
                                                                                                                                      '함께 '
                                                                                                                                      'edit_planar_face의 '
                                                                                                                                      'object_id/face_index/expected_geometry_crc로 '
                                                                                                                                      '전달'},
                                                                                                        'planar': {'type': 'boolean',
                                                                                                                   'description': '평면 '
                                                                                                                                  '여부입니다.'},
                                                                                                        'face_edit_supported': {'type': 'boolean',
                                                                                                                                'description': '이 '
                                                                                                                                               '면의 '
                                                                                                                                               '기본 '
                                                                                                                                               '편집 '
                                                                                                                                               '조건 '
                                                                                                                                               '충족 '
                                                                                                                                               '여부입니다. '
                                                                                                                                               '실행 '
                                                                                                                                               '전에는 '
                                                                                                                                               '형상 '
                                                                                                                                               '버전을 '
                                                                                                                                               '다시 '
                                                                                                                                               '검사합니다.'}}},
                                                                               'description': '관찰한 면 목록입니다.'},
                                                                     'faces_truncated': {'type': 'boolean',
                                                                                         'description': '면 목록이 일부 '
                                                                                                        '생략됐는지 '
                                                                                                        '여부입니다.'},
                                                                     'face_page': {'type': 'object',
                                                                                   'properties': {'offset': {'type': 'integer',
                                                                                                             'description': '이번 '
                                                                                                                            '페이지의 '
                                                                                                                            '시작 '
                                                                                                                            '위치입니다.'},
                                                                                                  'limit': {'type': 'integer',
                                                                                                            'description': '이번 '
                                                                                                                           '응답의 '
                                                                                                                           '최대 '
                                                                                                                           '항목 '
                                                                                                                           '수입니다.'},
                                                                                                  'returned': {'type': 'integer',
                                                                                                               'description': '이 '
                                                                                                                              '페이지에서 '
                                                                                                                              '반환한 '
                                                                                                                              '수입니다.'},
                                                                                                  'next_offset': {'type': ['integer',
                                                                                                                           'null'],
                                                                                                                  'description': '다음 '
                                                                                                                                 '페이지의 '
                                                                                                                                 '시작 '
                                                                                                                                 '위치입니다. '
                                                                                                                                 'null이면 '
                                                                                                                                 '다음 '
                                                                                                                                 '페이지가 '
                                                                                                                                 '없습니다.'},
                                                                                                  'complete': {'type': 'boolean',
                                                                                                               'description': '이 '
                                                                                                                              '객체의 '
                                                                                                                              '면 '
                                                                                                                              '목록을 '
                                                                                                                              '모두 '
                                                                                                                              '반환했는지 '
                                                                                                                              '나타냅니다.'}},
                                                                                   'description': '이 객체의 면 목록 페이지 '
                                                                                                  '정보입니다.'}}},
                                            'description': '조회한 객체와 요청한 속성입니다.'},
                                'matched_count': {'type': 'integer', 'description': '조회 조건에 맞는 객체 수입니다.'},
                                'offset': {'type': 'integer', 'description': '이번 페이지의 시작 위치입니다.'},
                                'limit': {'type': 'integer', 'description': '이번 응답의 최대 항목 수입니다.'},
                                'next_offset': {'type': ['integer', 'null'],
                                                'description': '다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.'},
                                'snapshot': {'type': 'string',
                                             'description': '후속 offset 페이지의 expected_snapshot에 그대로 전달'},
                                'editing': {'type': 'object',
                                            'properties': {},
                                            'description': '현재 편집 컨텍스트와 저장 대상 정보입니다.'},
                                'complete': {'type': 'boolean',
                                             'description': '요청한 객체 페이지가 완전한지 나타냅니다. 계층 하위의 관찰 상태는 각 '
                                                            'children_state에 있습니다.'},
                                'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                'next_step_guide': {'type': 'string',
                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'get_rhino_context': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'warnings': {'type': 'array',
                                                   'items': {'type': 'string'},
                                                   'description': '결과를 해석할 때 확인할 경고입니다.'},
                                      'document': {'type': 'object',
                                                   'properties': {'units': {'type': ['string', 'null'],
                                                                            'description': '문서 길이 단위'},
                                                                  'absolute_tolerance': {'type': ['number',
                                                                                                  'null'],
                                                                                         'description': '문서 길이 '
                                                                                                        '단위의 절대 '
                                                                                                        '허용오차'},
                                                                  'modified': {'type': ['boolean', 'null'],
                                                                               'description': '문서 수정 플래그'},
                                                                  'object_count': {'type': ['integer', 'null'],
                                                                                   'description': '객체 수'},
                                                                  'layer_count': {'type': ['number', 'null'],
                                                                                  'description': '레이어 수'},
                                                                  'angle_tolerance': {'type': ['number', 'null'],
                                                                                      'description': '라디안 단위의 각도 '
                                                                                                     '허용오차'}},
                                                   'description': '요청한 현재 문서 속성입니다. 관찰할 수 없는 값은 null입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'get_selection_references': {'type': 'object',
                              'properties': {'status': {'type': 'string',
                                                        'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                       '확인합니다.'},
                                             'objects': {'type': 'array',
                                                         'items': {'type': 'object'},
                                                         'description': '선택한 객체의 ID·등록 여부와 소유 Holon입니다.'},
                                             'holons': {'type': 'array',
                                                        'items': {'type': 'object'},
                                                        'description': '선택 객체를 소유한 Holon과 상위 Holon의 요약입니다.'},
                                             'plans': {'type': 'array',
                                                       'items': {'type': 'object'},
                                                       'description': '선택 객체를 참조하는 Plan의 요약입니다.'},
                                             'total_plans': {'type': 'integer', 'description': '참조 Plan 전체 개수'},
                                             'truncated': {'type': 'boolean',
                                                           'description': '현재 응답에서 결과가 잘렸는지 여부'},
                                             'ownership_live_verified': {'type': 'boolean',
                                                                         'description': '선택 객체 소유 관계의 현재 확인 여부. '
                                                                                        '선택이 없으면 false'},
                                             'references_live_verified': {'type': 'boolean',
                                                                          'description': '저장된 Plan·계층 참조를 현재 '
                                                                                         'Rhino에서 확인했는지 나타냅니다.'},
                                             'selection_total': {'type': 'integer', 'description': '선택된 객체 전체 수'},
                                             'selection_truncated': {'type': 'boolean',
                                                                     'description': '선택 조회의 일부가 생략되었는지 여부. Plan '
                                                                                    '목록의 truncated와 별개'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'resolve_targets': {'type': 'object',
                     'properties': {'status': {'type': 'string',
                                               'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                    'plan_id': {'type': 'string', 'description': 'Plan ID'},
                                    'step_id': {'description': 'Step ID'},
                                    'revision': {'type': 'integer',
                                                 'description': 'Plan의 저장 리비전입니다. 변경 검사에는 현재 loop_no도 함께 사용합니다.'},
                                    'scene_ids': {'type': 'array',
                                                  'items': {},
                                                  'description': 'Plan에 지정한 Scene 컨텍스트입니다.'},
                                    'holon_ids': {'type': 'array',
                                                  'items': {},
                                                  'description': 'Plan에 명시한 Holon 대상입니다. 빈 배열이면 지정 대상이 없습니다.'},
                                    'holons': {'type': 'array',
                                               'items': {'type': 'object'},
                                               'description': '저장된 대상 Holon의 요약입니다.'},
                                    'live_verified': {'type': 'boolean',
                                                      'description': '대상의 현재 Rhino 상태를 확인했는지 나타냅니다.'},
                                    'source': {'type': 'string', 'description': '대상 정보의 출처입니다. 현재는 plan입니다.'},
                                    'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                    'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                    'next_step_guide': {'type': 'string',
                                                        'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                       '반환합니다.'}}},
 'capture_conditioning_pass': {'type': 'object',
                               'properties': {'status': {'type': 'string',
                                                         'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                        '확인합니다.'},
                                              'frames_requested': {'type': 'integer', 'description': '요청 프레임 수'},
                                              'frames_captured': {'type': 'integer',
                                                                  'description': '성공한 캡처 청크의 프레임 수입니다.'},
                                              'passes': {'type': 'array',
                                                         'items': {'type': 'string'},
                                                         'description': '생성한 패스 종류'},
                                              'resolution': {'type': 'array',
                                                             'items': {'type': 'number'},
                                                             'description': '출력 이미지 해상도 [너비, 높이]'},
                                              'fps': {'type': 'number', 'description': '영상 프레임 레이트'},
                                              'errors': {'type': 'array',
                                                         'items': {},
                                                         'description': '실패한 청크의 프레임 범위와 메시지. 부분 생성 파일이 남을 수 있음'},
                                              'out_dir': {'type': 'string',
                                                          'description': '패스별 PNG와 '
                                                                         'doc.json/camera.json/zrange.csv/summary.json을 '
                                                                         '쓰는 폴더'},
                                              'camera_json': {'type': 'string',
                                                              'description': '전체 계획 경로 기록. '
                                                                             'frames[].camera/target/lens_mm를 '
                                                                             '포함하며 부분 캡처에도 계획은 전체 길이'},
                                              'videos': {'type': 'object',
                                                         'properties': {'rgb': {'description': '조립된 RGB 영상 경로입니다. '
                                                                                               '조립하지 못하면 null입니다.',
                                                                                'type': ['string', 'null']}},
                                                         'description': '완전 캡처 후 패스별 MP4. ffmpeg 조립 실패는 null이며 부분 '
                                                                        '캡처에는 빈 객체일 수 있음'},
                                              'document': {'type': 'object',
                                                           'properties': {},
                                                           'description': '원본 문서·단위·뷰·경계 정보입니다.'},
                                              'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                              'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                              'next_step_guide': {'type': 'string',
                                                                  'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                 '경우에만 반환합니다.'}}},
 'capture_rhino_inspection': {'type': 'object',
                              'properties': {'status': {'type': 'string', 'description': '이미지 캡처의 처리 상태입니다.'},
                                             'complete': {'type': 'boolean',
                                                          'description': '요청한 모든 타일을 캡처했는지 나타냅니다.'},
                                             'tiles': {'type': 'array',
                                                       'items': {'type': 'object',
                                                                 'properties': {'index': {'type': 'integer',
                                                                                          'description': '0부터 '
                                                                                                         '시작하는 항목 '
                                                                                                         '인덱스'},
                                                                                'status': {'type': 'string',
                                                                                           'description': '현재 처리의 '
                                                                                                          '상태입니다. '
                                                                                                          '오류이면 '
                                                                                                          'message와 '
                                                                                                          'error_code를 '
                                                                                                          '확인합니다.'},
                                                                                'direction': {'type': 'string',
                                                                                              'description': '캡처한 '
                                                                                                             '시점입니다.'}}},
                                                       'description': '타일별 캡처 결과와 관찰 범위입니다. 실패한 타일도 포함합니다.'},
                                             'image_file': {'type': 'object',
                                                            'properties': {'status': {'type': 'string',
                                                                                      'description': '파일 저장 '
                                                                                                     '결과입니다. '
                                                                                                     'saved일 때 '
                                                                                                     'path를 사용할 수 '
                                                                                                     '있습니다.'},
                                                                           'path': {'type': 'string',
                                                                                    'description': '프로젝트 기준 PNG '
                                                                                                   '상대 경로. '
                                                                                                   'output_refs에 '
                                                                                                   '기록할 때는 이 문자열만 '
                                                                                                   '사용'},
                                                                           'lifetime': {'type': 'string',
                                                                                        'description': 'plan은 '
                                                                                                       'Plan 산출물, '
                                                                                                       'connection은 '
                                                                                                       '연결 정리까지의 '
                                                                                                       '임시 파일'},
                                                                           'bytes': {'type': 'integer',
                                                                                     'description': '파일 바이트 수'},
                                                                           'sha256': {'type': 'string',
                                                                                      'description': '파일 해시.'}},
                                                            'description': 'PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 '
                                                                           '이미지가 제공될 수 있음'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'get_current_viewcapture': {'type': 'object',
                             'properties': {'image_file': {'type': 'object',
                                                           'properties': {'status': {'type': 'string',
                                                                                     'description': '파일 저장 결과입니다. '
                                                                                                    'saved일 때 '
                                                                                                    'path를 사용할 수 '
                                                                                                    '있습니다.'},
                                                                          'path': {'type': 'string',
                                                                                   'description': '프로젝트 기준 PNG 상대 '
                                                                                                  '경로. '
                                                                                                  'output_refs에 '
                                                                                                  '기록할 때는 이 문자열만 '
                                                                                                  '사용'},
                                                                          'lifetime': {'type': 'string',
                                                                                       'description': 'plan은 Plan '
                                                                                                      '산출물, '
                                                                                                      'connection은 '
                                                                                                      '연결 정리까지의 '
                                                                                                      '임시 파일'},
                                                                          'bytes': {'type': 'integer',
                                                                                    'description': '파일 바이트 수'},
                                                                          'sha256': {'type': 'string',
                                                                                     'description': '파일 해시.'}},
                                                           'description': 'PNG 저장 결과입니다. 이미지 전달 여부와 별도로 확인합니다.'},
                                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                            'next_step_guide': {'type': 'string',
                                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                               '경우에만 반환합니다.'},
                                            'status': {'type': 'string', 'description': '이미지 캡처의 처리 상태입니다.'}}},
 'get_defined_viewcapture': {'type': 'object',
                             'properties': {'image_file': {'type': 'object',
                                                           'properties': {'status': {'type': 'string',
                                                                                     'description': '파일 저장 결과입니다. '
                                                                                                    'saved일 때 '
                                                                                                    'path를 사용할 수 '
                                                                                                    '있습니다.'},
                                                                          'path': {'type': 'string',
                                                                                   'description': '프로젝트 기준 PNG 상대 '
                                                                                                  '경로. '
                                                                                                  'output_refs에 '
                                                                                                  '기록할 때는 이 문자열만 '
                                                                                                  '사용'},
                                                                          'lifetime': {'type': 'string',
                                                                                       'description': 'plan은 Plan '
                                                                                                      '산출물, '
                                                                                                      'connection은 '
                                                                                                      '연결 정리까지의 '
                                                                                                      '임시 파일'},
                                                                          'bytes': {'type': 'integer',
                                                                                    'description': '파일 바이트 수'},
                                                                          'sha256': {'type': 'string',
                                                                                     'description': '파일 해시.'}},
                                                           'description': 'PNG 저장 결과입니다. 실제 치수와 축소 경고는 캡처 메타데이터에서 '
                                                                          '확인합니다.'},
                                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                            'next_step_guide': {'type': 'string',
                                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                               '경우에만 반환합니다.'},
                                            'status': {'type': 'string', 'description': '이미지 캡처의 처리 상태입니다.'}}},
 'assign_material': {'type': 'object',
                     'properties': {'status': {'type': 'string',
                                               'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                    'material_id': {'type': 'string', 'description': '라이브러리 재료 ID'},
                                    'applied_count': {'type': 'integer',
                                                      'description': '처리 성공한 객체 수. requested_count와 비교하며 실제 변경 수와 '
                                                                     '구분'},
                                    'requested_count': {'type': 'integer', 'description': '요청한 수'},
                                    'render_material_applied': {'type': 'boolean',
                                                                'description': '렌더 재료를 적용하도록 요청했는지 나타냅니다.'},
                                    'material_metadata_attached': {'type': 'boolean',
                                                                   'description': '재료 메타데이터가 부착됐는지 여부'},
                                    'rhino_material_name': {'type': 'string', 'description': 'Rhino에 적용한 재료명'},
                                    'ue_material_slot': {'type': 'string', 'description': '재료 슬롯명'},
                                    'applied_guids': {'type': 'array',
                                                      'items': {'type': 'string'},
                                                      'description': '처리가 성공한 객체 GUID입니다. 실제 변경이 확인된 객체는 '
                                                                     'changed_guids에 있습니다.'},
                                    'metadata_attached': {'type': 'boolean', 'description': '요청한 메타데이터 적용 여부입니다.'},
                                    'layer_path': {'type': ['string', 'null'],
                                                   'description': '대상의 레이어 경로입니다. 제공되지 않으면 null입니다.'},
                                    'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                    'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                    'next_step_guide': {'type': 'string',
                                                        'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                       '반환합니다.'}}},
 'edit_planar_face': {'type': 'object',
                      'properties': {'status': {'type': 'string',
                                                'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                     'result': {'type': 'object',
                                                'properties': {'edited': {'type': 'boolean',
                                                                          'description': '대상 객체와 이전 CRC를 확인하고 편집을 '
                                                                                         '적용했는지 나타냅니다.'},
                                                               'object_id': {'type': 'string',
                                                                             'description': 'Rhino 객체 GUID'},
                                                               'previous_geometry_crc': {'type': 'number',
                                                                                         'description': '편집 전 형상 '
                                                                                                        'CRC'},
                                                               'geometry_crc': {'type': 'number',
                                                                                'description': '편집 후 CRC. 면 인덱스도 '
                                                                                               '바뀔 수 있어 추가 면 편집 전 '
                                                                                               '새 faces 관찰 필요'}},
                                                'description': '단일 면의 편집 결과입니다.'},
                                     'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                     'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                     'next_step_guide': {'type': 'string',
                                                         'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                        '반환합니다.'}}},
 'edit_planar_faces': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'result': {'type': 'object',
                                                 'properties': {'status': {'type': 'string',
                                                                           'description': '현재 처리의 상태입니다. 오류이면 '
                                                                                          'message와 error_code를 '
                                                                                          '확인합니다.'},
                                                                'complete': {'type': 'boolean',
                                                                             'description': '모든 항목 적용이 확인되었는지 여부'},
                                                                'requested_count': {'type': 'integer',
                                                                                    'description': '요청한 수'},
                                                                'applied_count': {'type': 'integer',
                                                                                  'description': '실제 적용된 수'},
                                                                'mutation_state': {'type': 'string',
                                                                                   'description': 'not_started/applied/partial/unknown '
                                                                                                  '등. '
                                                                                                  'partial·unknown은 '
                                                                                                  '전체 배치 재실행 금지'},
                                                                'items': {'type': 'array',
                                                                          'items': {'type': 'object',
                                                                                    'properties': {'status': {'type': 'string',
                                                                                                              'description': '항목 '
                                                                                                                             '처리 '
                                                                                                                             '상태입니다. '
                                                                                                                             'applied, '
                                                                                                                             'rejected, '
                                                                                                                             'failed, '
                                                                                                                             'unknown, '
                                                                                                                             'not_attempted '
                                                                                                                             '중 '
                                                                                                                             '하나입니다.'},
                                                                                                   'edited': {'type': 'boolean',
                                                                                                              'description': '형상 '
                                                                                                                             '편집 '
                                                                                                                             '적용 '
                                                                                                                             '여부'},
                                                                                                   'previous_geometry_crc': {'type': 'number',
                                                                                                                             'description': '편집 '
                                                                                                                                            '전 '
                                                                                                                                            '형상 '
                                                                                                                                            'CRC'},
                                                                                                   'geometry_crc': {'type': 'number',
                                                                                                                    'description': '변경 '
                                                                                                                                   '후 '
                                                                                                                                   'CRC. '
                                                                                                                                   '다음 '
                                                                                                                                   '면 '
                                                                                                                                   '편집 '
                                                                                                                                   '전 '
                                                                                                                                   '면 '
                                                                                                                                   '인덱스를 '
                                                                                                                                   '다시 '
                                                                                                                                   '관찰'}}},
                                                                          'description': '입력 순서의 항목별 결과. '
                                                                                         'applied/rejected/failed/unknown/not_attempted와 '
                                                                                         'stage/message 등을 보존'}},
                                                 'description': '배치 결과. 준비 실패는 교체 전이며 교체 중 실패는 부분 적용일 수 있음'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'list_materials': {'type': 'object',
                    'properties': {'total': {'type': 'integer', 'description': '조건에 일치하는 라이브러리 재료 수입니다.'},
                                   'materials': {'type': 'array',
                                                 'items': {'type': 'object',
                                                           'properties': {'name': {'type': 'string',
                                                                                   'description': '저장된 이름'},
                                                                          'category': {'type': 'string',
                                                                                       'description': '분류'}}},
                                                 'description': '재료의 이름·분류와 요청한 속성입니다.'},
                                   'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                   'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                   'next_step_guide': {'type': 'string',
                                                       'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                      '반환합니다.'}}},
 'setup_modeling': {'type': 'object',
                    'properties': {'status': {'type': 'string',
                                              'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                   'applied': {'type': 'boolean',
                                               'description': '모든 지정 속성이 일치하는지 여부. false여도 누락 항목 생성·일부 변경이 있었을 수 '
                                                              '있음'},
                                   'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                   'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                   'next_step_guide': {'type': 'string',
                                                       'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                      '반환합니다.'}}},
 'execute_project_python': {'type': 'object',
                            'properties': {'status': {'type': 'string',
                                                      'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                     '확인합니다.'},
                                           'completed': {'type': 'boolean',
                                                         'description': 'Rhino 실행 완료가 확인됐는지 나타냅니다.'},
                                           'request_id': {'type': 'string',
                                                          'description': '미완료·불확실성·결과 페이지를 get_rhino_execution으로 '
                                                                         '회수할 정확한 ID'},
                                           'artifact_dir': {'type': ['string', 'null'],
                                                            'description': '실행에 사용한 Plan·Loop 산출물 폴더입니다.'},
                                           'result': {'description': '실행 코드가 정한 JSON 값입니다.'},
                                           'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                           'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                           'next_step_guide': {'type': 'string',
                                                               'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                              '반환합니다.'},
                                           'mutation_state': {'type': 'string',
                                                              'description': '변경 적용 상태입니다. partial 또는 unknown이면 '
                                                                             '같은 수정을 다시 실행하기 전에 현재 상태를 확인합니다.'},
                                           'result_page': {'type': 'object',
                                                           'description': '결과를 나누어 읽기 위한 정보입니다.',
                                                           'properties': {'type': {'type': 'string',
                                                                                   'description': '결과 유형입니다. '
                                                                                                  'object, array, '
                                                                                                  'string, scalar '
                                                                                                  '중 하나입니다.'},
                                                                          'unit': {'type': 'string',
                                                                                   'description': '문자열 페이지의 위치 '
                                                                                                  '단위입니다.'},
                                                                          'available_fields': {'type': 'array',
                                                                                               'description': '조회할 '
                                                                                                              '수 '
                                                                                                              '있는 '
                                                                                                              '최상위 '
                                                                                                              '결과 '
                                                                                                              '필드입니다.',
                                                                                               'items': {'type': 'string'}},
                                                                          'pages': {'type': 'object',
                                                                                    'description': '결과 필드 이름별 페이지 '
                                                                                                   '정보입니다. 배열·문자열 '
                                                                                                   '전체는 result 키를 '
                                                                                                   '사용합니다.',
                                                                                    'additionalProperties': {'type': 'object',
                                                                                                             'description': '해당 '
                                                                                                                            '필드의 '
                                                                                                                            '페이지 '
                                                                                                                            '정보입니다.',
                                                                                                             'properties': {'total': {'type': 'integer',
                                                                                                                                      'description': '전체 '
                                                                                                                                                     '항목 '
                                                                                                                                                     '수 '
                                                                                                                                                     '또는 '
                                                                                                                                                     '문자열 '
                                                                                                                                                     '길이입니다.'},
                                                                                                                            'offset': {'type': 'integer',
                                                                                                                                       'description': '이번 '
                                                                                                                                                      '페이지의 '
                                                                                                                                                      '시작 '
                                                                                                                                                      '위치입니다.'},
                                                                                                                            'returned': {'type': 'integer',
                                                                                                                                         'description': '반환한 '
                                                                                                                                                        '항목 '
                                                                                                                                                        '수 '
                                                                                                                                                        '또는 '
                                                                                                                                                        '문자열 '
                                                                                                                                                        '길이입니다.'},
                                                                                                                            'next_offset': {'type': ['integer',
                                                                                                                                                     'null'],
                                                                                                                                            'description': '다음 '
                                                                                                                                                           '페이지의 '
                                                                                                                                                           'offset입니다. '
                                                                                                                                                           'null이면 '
                                                                                                                                                           '마지막 '
                                                                                                                                                           '페이지입니다.'}}}}}},
                                           'result_error': {'type': ['string', 'null'],
                                                            'description': '실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.'},
                                           'result_display_error': {'type': ['string', 'null'],
                                                                    'description': '결과를 응답에 표시하는 중 발생한 오류입니다.'}}},
 'execute_rhino_script': {'type': 'object',
                          'properties': {'status': {'type': 'string',
                                                    'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                   '확인합니다.'},
                                         'completed': {'type': 'boolean',
                                                       'description': 'Rhino 실행 완료가 확인됐는지 나타냅니다. 변경 결과는 '
                                                                      'mutation_state와 result에서 확인합니다.'},
                                         'request_id': {'type': 'string',
                                                        'description': '필요할 때 get_rhino_execution으로 같은 요청을 조회하는 '
                                                                       'ID'},
                                         'result': {'description': '실행 코드가 정한 JSON 값입니다.'},
                                         'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                         'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                         'next_step_guide': {'type': 'string',
                                                             'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                            '반환합니다.'},
                                         'mutation_state': {'type': 'string',
                                                            'description': '변경 적용 상태입니다. partial 또는 unknown이면 같은 '
                                                                           '수정을 다시 실행하기 전에 현재 상태를 확인합니다.'},
                                         'result_page': {'type': 'object',
                                                         'description': '결과를 나누어 읽기 위한 정보입니다.',
                                                         'properties': {'type': {'type': 'string',
                                                                                 'description': '결과 유형입니다. '
                                                                                                'object, array, '
                                                                                                'string, scalar 중 '
                                                                                                '하나입니다.'},
                                                                        'unit': {'type': 'string',
                                                                                 'description': '문자열 페이지의 위치 '
                                                                                                '단위입니다.'},
                                                                        'available_fields': {'type': 'array',
                                                                                             'description': '조회할 '
                                                                                                            '수 있는 '
                                                                                                            '최상위 '
                                                                                                            '결과 '
                                                                                                            '필드입니다.',
                                                                                             'items': {'type': 'string'}},
                                                                        'pages': {'type': 'object',
                                                                                  'description': '결과 필드 이름별 페이지 '
                                                                                                 '정보입니다. 배열·문자열 '
                                                                                                 '전체는 result 키를 '
                                                                                                 '사용합니다.',
                                                                                  'additionalProperties': {'type': 'object',
                                                                                                           'description': '해당 '
                                                                                                                          '필드의 '
                                                                                                                          '페이지 '
                                                                                                                          '정보입니다.',
                                                                                                           'properties': {'total': {'type': 'integer',
                                                                                                                                    'description': '전체 '
                                                                                                                                                   '항목 '
                                                                                                                                                   '수 '
                                                                                                                                                   '또는 '
                                                                                                                                                   '문자열 '
                                                                                                                                                   '길이입니다.'},
                                                                                                                          'offset': {'type': 'integer',
                                                                                                                                     'description': '이번 '
                                                                                                                                                    '페이지의 '
                                                                                                                                                    '시작 '
                                                                                                                                                    '위치입니다.'},
                                                                                                                          'returned': {'type': 'integer',
                                                                                                                                       'description': '반환한 '
                                                                                                                                                      '항목 '
                                                                                                                                                      '수 '
                                                                                                                                                      '또는 '
                                                                                                                                                      '문자열 '
                                                                                                                                                      '길이입니다.'},
                                                                                                                          'next_offset': {'type': ['integer',
                                                                                                                                                   'null'],
                                                                                                                                          'description': '다음 '
                                                                                                                                                         '페이지의 '
                                                                                                                                                         'offset입니다. '
                                                                                                                                                         'null이면 '
                                                                                                                                                         '마지막 '
                                                                                                                                                         '페이지입니다.'}}}}}},
                                         'result_error': {'type': ['string', 'null'],
                                                          'description': '실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.'},
                                         'result_display_error': {'type': ['string', 'null'],
                                                                  'description': '결과를 응답에 표시하는 중 발생한 오류입니다.'}}},
 'get_rhino_execution': {'type': 'object',
                         'properties': {'request_id': {'type': 'string',
                                                       'description': '보관된 실행 요청 ID입니다. 같은 실행의 상태나 다음 결과 페이지 조회에 '
                                                                      '사용합니다.'},
                                        'completed': {'type': 'boolean',
                                                      'description': '최종 Rhino 처리 근거와 CLI 종료가 모두 확인되었는지 여부. '
                                                                     'native_completed와 다를 수 있음'},
                                        'status': {'type': 'string',
                                                   'description': '보관된 실행의 상태입니다. 조회 호출 자체의 성공과 구분합니다.'},
                                        'result': {'description': '실행 코드가 정한 JSON 값입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'},
                                        'mutation_state': {'type': 'string',
                                                           'description': '변경 적용 상태입니다. partial 또는 unknown이면 같은 '
                                                                          '수정을 다시 실행하기 전에 현재 상태를 확인합니다.'},
                                        'result_page': {'type': 'object',
                                                        'description': '결과를 나누어 읽기 위한 정보입니다.',
                                                        'properties': {'type': {'type': 'string',
                                                                                'description': '결과 유형입니다. object, '
                                                                                               'array, string, '
                                                                                               'scalar 중 하나입니다.'},
                                                                       'unit': {'type': 'string',
                                                                                'description': '문자열 페이지의 위치 '
                                                                                               '단위입니다.'},
                                                                       'available_fields': {'type': 'array',
                                                                                            'description': '조회할 수 '
                                                                                                           '있는 '
                                                                                                           '최상위 '
                                                                                                           '결과 '
                                                                                                           '필드입니다.',
                                                                                            'items': {'type': 'string'}},
                                                                       'pages': {'type': 'object',
                                                                                 'description': '결과 필드 이름별 페이지 '
                                                                                                '정보입니다. 배열·문자열 '
                                                                                                '전체는 result 키를 '
                                                                                                '사용합니다.',
                                                                                 'additionalProperties': {'type': 'object',
                                                                                                          'description': '해당 '
                                                                                                                         '필드의 '
                                                                                                                         '페이지 '
                                                                                                                         '정보입니다.',
                                                                                                          'properties': {'total': {'type': 'integer',
                                                                                                                                   'description': '전체 '
                                                                                                                                                  '항목 '
                                                                                                                                                  '수 '
                                                                                                                                                  '또는 '
                                                                                                                                                  '문자열 '
                                                                                                                                                  '길이입니다.'},
                                                                                                                         'offset': {'type': 'integer',
                                                                                                                                    'description': '이번 '
                                                                                                                                                   '페이지의 '
                                                                                                                                                   '시작 '
                                                                                                                                                   '위치입니다.'},
                                                                                                                         'returned': {'type': 'integer',
                                                                                                                                      'description': '반환한 '
                                                                                                                                                     '항목 '
                                                                                                                                                     '수 '
                                                                                                                                                     '또는 '
                                                                                                                                                     '문자열 '
                                                                                                                                                     '길이입니다.'},
                                                                                                                         'next_offset': {'type': ['integer',
                                                                                                                                                  'null'],
                                                                                                                                         'description': '다음 '
                                                                                                                                                        '페이지의 '
                                                                                                                                                        'offset입니다. '
                                                                                                                                                        'null이면 '
                                                                                                                                                        '마지막 '
                                                                                                                                                        '페이지입니다.'}}}}}},
                                        'result_error': {'type': ['string', 'null'],
                                                         'description': '실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.'},
                                        'result_display_error': {'type': ['string', 'null'],
                                                                 'description': '결과를 응답에 표시하는 중 발생한 오류입니다.'}}},
 'save_rhino_document': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'saved': {'type': ['boolean', 'null'],
                                                  'description': 'true는 확인된 저장, false는 확인된 실패, null은 미확정이며 '
                                                                 'requires_reconciliation=true'},
                                        'modified': {'type': 'boolean', 'description': '저장 확인 직후의 문서 수정 플래그입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'add_scene_objects': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'failed_indices': {'type': 'array',
                                                         'items': {},
                                                         'description': '입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 '
                                                                        '시작합니다.'},
                                      'already_present_indices': {'type': 'array',
                                                                  'items': {},
                                                                  'description': '이미 포함되어 변경하지 않은 입력 위치. Holon을 '
                                                                                 '통해 포함된 경우도 포함'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'create_design_scene': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'scene': {'type': 'object',
                                                  'properties': {'scene_id': {'type': 'string',
                                                                              'description': 'Scene ID'},
                                                                 'revision': {'type': 'integer',
                                                                              'description': 'Scene의 저장 리비전입니다. '
                                                                                             '생성 시 0입니다.'}},
                                                  'description': '생성한 Scene의 확인 정보입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'focus_holons': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                 'zoom_selected': {'type': 'boolean', 'description': '선택 객체로 줌했는지 여부'},
                                 'isolated': {'type': 'boolean', 'description': '대상을 격리했는지 여부'},
                                 'locked_context_remains_visible': {'type': 'boolean',
                                                                    'description': '잠긴 주변 객체를 계속 표시하는지 여부'},
                                 'restore_visibility_command': {'type': 'string',
                                                                'description': '격리한 객체의 가시성을 복구하는 명령입니다.'},
                                 'model_path': {'type': 'string', 'description': '저장된 모델의 경로'},
                                 'viewport_id': {'type': 'string', 'description': '포커스된 실제 모델 뷰포트 GUID'},
                                 'selected_ids': {'type': 'array',
                                                  'items': {'type': 'string'},
                                                  'description': '포커스할 때 실제로 선택한 Rhino 객체 GUID입니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'get_design_scene': {'type': 'object',
                      'properties': {'status': {'type': 'string',
                                                'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                     'scene': {'type': 'object',
                                               'properties': {'name': {'type': 'string', 'description': '저장된 이름'},
                                                              'units': {'type': 'string',
                                                                        'description': 'Scene에 기록한 길이 단위입니다.'},
                                                              'revision': {'type': 'integer',
                                                                           'description': '저장 상태의 revision'},
                                                              'holons': {'type': 'integer',
                                                                         'description': 'Scene의 Holon 개수'},
                                                              'objects': {'type': ['integer', 'null'],
                                                                          'description': '저장된 구성원 수. 직접 등록·제외 '
                                                                                         'override가 있으면 null이며 빈 '
                                                                                         'Scene을 뜻하지 않음'},
                                                              'direct_objects': {'type': 'integer',
                                                                                 'description': '직접 등록된 객체 수'},
                                                              'live_verified': {'type': 'boolean',
                                                                                'description': 'Scene 구성원을 현재 '
                                                                                               'Rhino에서 확인했는지 '
                                                                                               '나타냅니다.'}},
                                               'description': 'Scene의 저장 요약입니다.'},
                                     'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                     'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                     'next_step_guide': {'type': 'string',
                                                         'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                        '반환합니다.'}}},
 'get_ontological_holon': {'type': 'object',
                           'properties': {'status': {'type': 'string',
                                                     'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                    '확인합니다.'},
                                          'holon': {'type': 'object',
                                                    'properties': {'name': {'type': 'string',
                                                                            'description': '저장된 이름'},
                                                                   'availability': {'type': 'string',
                                                                                    'description': 'Holon의 등록 상태 '
                                                                                                   '또는 현재 관찰 '
                                                                                                   '상태입니다. '
                                                                                                   'live_verified와 '
                                                                                                   '함께 확인합니다.'},
                                                                   'object_count': {'type': 'integer',
                                                                                    'description': '객체 수'},
                                                                   'live_verified': {'type': 'boolean',
                                                                                     'description': 'Holon 구성원을 '
                                                                                                    '현재 Rhino에서 '
                                                                                                    '확인했는지 '
                                                                                                    '나타냅니다.'}},
                                                    'description': '조회한 Holon의 요약입니다.'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'}}},
 'get_scene_objects': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'objects': {'type': 'array',
                                                  'items': {'type': 'object'},
                                                  'description': '현재 연결 모델에서 확인한 Scene 객체와 요청한 속성입니다.'},
                                      'total': {'type': 'integer', 'description': '현재 연결 모델에서 확인한 Scene 객체 수입니다.'},
                                      'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                      'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                      'truncated': {'type': 'boolean',
                                                    'description': '뒤 페이지가 남았는지 여부. 다음 offset은 현재 offset+objects '
                                                                   '길이'},
                                      'live_verified': {'type': 'boolean', 'description': '현재 Rhino 상태를 확인했는지 여부'},
                                      'model_path': {'type': 'string', 'description': '관찰한 연결 모델의 경로입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'list_design_scenes': {'type': 'object',
                        'properties': {'status': {'type': 'string',
                                                  'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                       'scenes': {'type': 'array',
                                                  'items': {'type': 'object'},
                                                  'description': '저장된 Scene의 이름과 요청한 속성입니다.'},
                                       'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                       'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                       'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                       'truncated': {'type': 'boolean',
                                                     'description': '뒤 페이지가 남았는지 여부. 같은 필터로 offset+scenes 길이부터 계속 '
                                                                    '조회'},
                                       'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                       'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                       'next_step_guide': {'type': 'string',
                                                           'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                          '반환합니다.'}}},
 'list_ontological_holons': {'type': 'object',
                             'properties': {'status': {'type': 'string',
                                                       'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                      '확인합니다.'},
                                            'holons': {'type': 'array',
                                                       'items': {'type': 'object'},
                                                       'description': '등록된 Holon의 저장 요약입니다.'},
                                            'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                            'live_verified': {'type': 'boolean',
                                                              'description': 'Holon을 현재 Rhino에서 확인했는지 나타냅니다.'},
                                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                            'next_step_guide': {'type': 'string',
                                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                               '경우에만 반환합니다.'}}},
 'remove_ontological_holon': {'type': 'object',
                              'properties': {'status': {'type': 'string',
                                                        'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                       '확인합니다.'},
                                             'holon': {'type': 'object',
                                                       'properties': {'holon_id': {'type': 'string',
                                                                                   'description': '등록 해제한 Holon '
                                                                                                  'ID입니다.'},
                                                                      'status': {'type': 'string',
                                                                                 'description': 'Holon 등록 해제 '
                                                                                                '상태입니다.'},
                                                                      'live_verified': {'type': 'boolean',
                                                                                        'description': '현재 Rhino '
                                                                                                       '상태를 확인했는지 '
                                                                                                       '여부'}},
                                                       'description': 'Holon 등록 해제 결과입니다.'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'remove_scene_objects': {'type': 'object',
                          'properties': {'status': {'type': 'string',
                                                    'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                   '확인합니다.'},
                                         'failed_indices': {'type': 'array',
                                                            'items': {},
                                                            'description': '입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. '
                                                                           '0부터 시작합니다.'},
                                         'already_absent_indices': {'type': 'array',
                                                                    'items': {},
                                                                    'description': 'Scene에 이미 포함되지 않은 입력 항목의 '
                                                                                   '인덱스입니다. 0부터 시작합니다.'},
                                         'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                         'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                         'next_step_guide': {'type': 'string',
                                                             'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                            '반환합니다.'}}},
 'sync_ontological_holon': {'type': 'object',
                            'properties': {'status': {'type': 'string',
                                                      'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                     '확인합니다.'},
                                           'checked': {'type': 'integer', 'description': '확인한 Holon 수'},
                                           'changed': {'type': 'integer',
                                                       'description': '실제 대장 갱신 수. 변경 없으면 새 리비전도 없음'},
                                           'unavailable': {'type': 'integer',
                                                           'description': '상태가 present가 아닌 등록 수'},
                                           'problems': {'type': 'array',
                                                        'items': {},
                                                        'description': '항목별 문제. 관련 없는 유효 등록은 함께 갱신될 수 있음'},
                                           'scene_revisions': {'type': 'object',
                                                               'properties': {},
                                                               'description': '갱신한 Scene ID와 저장 리비전의 대응입니다.'},
                                           'live_verified': {'type': 'boolean',
                                                             'description': '문제 없이 모든 대상의 현재 상태를 확인했는지 나타냅니다.'},
                                           'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                           'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                           'next_step_guide': {'type': 'string',
                                                               'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                              '반환합니다.'}}},
 'update_design_scene': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'scene': {'type': 'object',
                                                  'properties': {'scene_id': {'type': 'string',
                                                                              'description': '이후 Scene 조회에 재사용할 '
                                                                                             '핸들'},
                                                                 'revision': {'type': 'integer',
                                                                              'description': 'Scene의 저장 리비전입니다. '
                                                                                             '실제 파일 연결이 바뀔 때 '
                                                                                             '증가합니다.'}},
                                                  'description': '수정한 Scene의 확인 정보입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'upsert_ontological_holon': {'type': 'object',
                              'properties': {'status': {'type': 'string',
                                                        'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                       '확인합니다.'},
                                             'holon': {'type': 'object',
                                                       'properties': {'holon_id': {'type': 'string',
                                                                                   'description': '등록한 Holon '
                                                                                                  'ID입니다. '
                                                                                                  '조회·동기화·포커스에 '
                                                                                                  '사용합니다.'},
                                                                      'availability': {'type': 'string',
                                                                                       'description': '대상 이용 가능 '
                                                                                                      '상태'},
                                                                      'object_count': {'type': 'integer',
                                                                                       'description': '객체 수'},
                                                                      'live_verified': {'type': 'boolean',
                                                                                        'description': '현재 '
                                                                                                       'Rhino에서 '
                                                                                                       '등록을 확인했는지 '
                                                                                                       '나타냅니다.'}},
                                                       'description': '등록한 Holon의 확인 정보입니다.'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'get_object_intersections': {'type': 'object',
                              'properties': {'intersections': {'type': 'object',
                                                               'properties': {'number': {'type': 'integer',
                                                                                         'description': '양의 부피가 '
                                                                                                        '겹치는 객체 '
                                                                                                        '쌍의 '
                                                                                                        '수입니다.'}},
                                                               'description': '겹침 집계'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'resolve_object_intersection': {'type': 'object',
                                 'properties': {'status': {'type': 'string',
                                                           'description': '현재 처리의 상태입니다. 오류이면 message와 '
                                                                          'error_code를 확인합니다.'},
                                                'state': {'type': 'string',
                                                          'description': '검토 진행 상태입니다. awaiting_choice이면 비교 결과를 '
                                                                         '확인한 뒤 선택합니다.'},
                                                'skipped_pairs': {'type': 'number',
                                                                  'description': '건너뛴 쌍은 수정하지 않음. completed가 모든 '
                                                                                 '겹침 제거를 뜻하지 않음'},
                                                'message': {'type': 'string',
                                                            'description': '현재 결과 또는 오류의 설명입니다.'},
                                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                                'next_step_guide': {'type': 'string',
                                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                   '경우에만 반환합니다.'}}},
 'audit_asset_drawing': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'source_geometry': {'type': 'string',
                                                            'description': 'current/source_file_current/stale/not_checked. '
                                                                           'not_checked는 success여도 원본 비교 미실시'},
                                        'asset_id': {'type': 'string',
                                                     'description': '패키지 원본 ID. custom-*는 등록 자산 ID가 아님'},
                                        'checked_files': {'type': 'integer',
                                                          'description': '해시를 검사한 파일 수. 시각적 검토가 아님'},
                                        'failures': {'type': 'array',
                                                     'items': {},
                                                     'description': '실패 항목이 하나라도 있으면 status=error'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'generate_asset_drawing_views': {'type': 'object',
                                  'properties': {'status': {'type': 'string',
                                                            'description': '현재 처리의 상태입니다. 오류이면 message와 '
                                                                           'error_code를 확인합니다.'},
                                                 'package_dir': {'type': 'string',
                                                                 'description': '생성한 도면 패키지 폴더입니다.'},
                                                 'manifest': {'type': 'object',
                                                              'properties': {},
                                                              'description': '생성한 도면과 원본·축척·단위 기록입니다.'},
                                                 'message': {'type': 'string',
                                                             'description': '현재 결과 또는 오류의 설명입니다.'},
                                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                                 'next_step_guide': {'type': 'string',
                                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. '
                                                                                    '필요한 경우에만 반환합니다.'}}},
 'get_asset_drawing': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'plan_svg_uri': {'type': 'string',
                                                       'description': '저장된 평면 SVG를 읽는 리소스 URI입니다.'},
                                      'manifest': {'type': 'object',
                                                   'properties': {},
                                                   'description': '도면 패키지의 원본·파일·축척 기록입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'get_drawing_asset': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'asset': {'type': 'object',
                                                'properties': {'name': {'type': 'string', 'description': '저장된 이름'},
                                                               'file_available': {'type': 'boolean',
                                                                                  'description': '원본·등록 파일의 존재 '
                                                                                                 '여부'},
                                                               'model_status': {'type': 'string',
                                                                                'description': 'ready/needs_conversion/needs_refresh '
                                                                                               '등. source_only는 '
                                                                                               '원본이 있어도 배치 준비 안 '
                                                                                               '됨'},
                                                               'drawing_ready': {'type': 'boolean',
                                                                                 'description': '현재 원본에 대응하는 도면 '
                                                                                                '패키지가 준비됐는지 '
                                                                                                '나타냅니다.'}},
                                                'description': '선택한 도면 자산과 준비 상태입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'list_drawing_assets': {'type': 'object',
                         'properties': {'library_id': {'type': 'string',
                                                       'description': 'include_ids=true에서 유지되는 라이브러리 구분자'},
                                        'assets': {'type': 'array',
                                                   'items': {'type': 'object'},
                                                   'description': '도면 자산 목록입니다. 추가 준비가 필요한 항목에는 next_tool과 '
                                                                  'next_step_guide가 있습니다.'},
                                        'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                        'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                        'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                        'truncated': {'type': 'boolean',
                                                      'description': 'true이면 같은 필터로 offset+현재 항목 수부터 계속. '
                                                                     'next_offset 필드는 없음'},
                                        'purpose': {'type': 'string', 'description': '이 라이브러리의 용도입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'place_drawing_asset': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'asset_id': {'type': 'string', 'description': '자산 ID'},
                                        'object_guid': {'type': 'string',
                                                        'description': '삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 '
                                                                       '입력에 재사용'},
                                        'definition_created': {'type': 'boolean',
                                                               'description': '새 정의 생성 여부. 공유 정의 갱신 시 '
                                                                              'definition_refreshed/affected_existing_instances가 '
                                                                              '추가될 수 있음'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'prepare_drawing_asset': {'type': 'object',
                           'properties': {'status': {'type': 'string',
                                                     'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                    '확인합니다.'},
                                          'state': {'type': 'string',
                                                    'description': 'ready일 때만 source_3dm 제공. '
                                                                   'running/unconfirmed/failed는 error와 '
                                                                   'next_stage=null'},
                                          'ready_for_registration': {'type': 'boolean',
                                                                     'description': '현재 파일 해시에 대한 이미지 검토를 호출자가 '
                                                                                    '확인했는지 나타냅니다.'},
                                          'job_dir': {'type': 'string',
                                                      'description': '이후 단계 및 등록의 preparation_job에 재사용. status는 '
                                                                     '저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음'},
                                          'source_3dm': {'type': 'string',
                                                         'description': '검토 완료 최종 파일. register_drawing_asset에 검토한 '
                                                                        'name/asset_id와 함께 전달'},
                                          'next_stage': {'type': ['string', 'null'],
                                                         'description': '현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음'},
                                          'review_evidence': {'type': 'string',
                                                              'description': '저장된 검토 증거에 대한 설명입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'refresh_asset': {'type': 'object',
                   'properties': {'status': {'type': 'string',
                                             'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                  'registration_applied': {'type': 'boolean',
                                                           'description': 'true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음'},
                                  'source_path_preserved': {'type': 'boolean',
                                                            'description': '기존 원본 경로를 보존했는지 여부'},
                                  'rhino_linked_instances_updated': {'type': 'boolean',
                                                                     'description': 'false: 기존 Rhino 연결 인스턴스 재로드는 '
                                                                                    '별도'},
                                  'live_index_refreshed': {'type': 'boolean',
                                                           'description': 'false인데 게시가 적용됐다면 재연결하여 인덱스 갱신'},
                                  'asset': {'type': 'object', 'properties': {}, 'description': '갱신한 자산의 정보입니다.'},
                                  'model_path': {'type': 'string', 'description': '갱신한 라이브러리 3DM 경로입니다.'},
                                  'package_dir': {'type': 'string', 'description': '갱신한 도면 패키지 폴더입니다.'},
                                  'previous_files_retained': {'type': 'boolean',
                                                              'description': '이전 도면·매니페스트 백업·원본 리비전 사본 보존'},
                                  'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                  'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                  'next_step_guide': {'type': 'string',
                                                      'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                     '반환합니다.'}}},
 'register_drawing_asset': {'type': 'object',
                            'properties': {'status': {'type': 'string',
                                                      'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                     '확인합니다.'},
                                           'registration_applied': {'type': ['boolean', 'null'],
                                                                    'description': 'true면 게시 적용. 불명확한 오류는 null과 '
                                                                                   'requires_reconciliation; 단순 '
                                                                                   '재시도 금지'},
                                           'live_index_refreshed': {'type': 'boolean',
                                                                    'description': '게시 true·인덱스 false이면 등록을 반복하지 '
                                                                                   '말고 재연결'},
                                           'source_path_preserved': {'type': 'boolean',
                                                                     'description': '기존 원본 경로를 보존했는지 여부'},
                                           'linked_instances_may_update': {'type': 'boolean',
                                                                           'description': '교체로 기존 연결 인스턴스에 영향 가능'},
                                           'asset': {'type': 'object',
                                                     'properties': {},
                                                     'description': '등록한 자산의 정보입니다.'},
                                           'library_dir': {'type': 'string', 'description': '라이브러리 폴더'},
                                           'model_path': {'type': 'string', 'description': '저장된 모델의 경로'},
                                           'package_dir': {'type': 'string',
                                                           'description': '생성한 도면 패키지 폴더입니다. DXF와 치수는 mm 단위입니다.'},
                                           'manifest_path': {'type': 'string',
                                                             'description': '라이브러리 manifest.json 경로입니다.'},
                                           'previous_files_retained': {'type': 'boolean',
                                                                       'description': '교체 전 원본·도면·매니페스트 백업 보존'},
                                           'previous_source_sha256': {'description': '기존 원본 해시. 없으면 null',
                                                                      'type': ['string', 'null']},
                                           'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                           'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                           'next_step_guide': {'type': 'string',
                                                               'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                              '반환합니다.'}}},
 'search_asset_repository': {'type': 'object',
                             'properties': {'total': {'type': 'integer',
                                                      'description': '전체 매치 수. assets는 limit까지이며 offset/has_more '
                                                                     '없음'},
                                            'assets': {'type': 'array',
                                                       'items': {'type': 'object'},
                                                       'description': '검색된 자산과 준비 상태입니다. id를 후속 도구의 asset_id로 '
                                                                      '사용합니다.'},
                                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                            'next_step_guide': {'type': 'string',
                                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                               '경우에만 반환합니다.'}}},
 'search_drawing_assets': {'type': 'object',
                           'properties': {'assets': {'type': 'array',
                                                     'items': {'type': 'object'},
                                                     'description': '검색된 도면 자산과 준비 상태입니다.'},
                                          'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                          'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                          'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                          'truncated': {'type': 'boolean',
                                                        'description': 'true이면 같은 필터로 offset+현재 항목 수부터 계속'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'}}},
 'get_diagram_asset': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'asset': {'type': 'object',
                                                'properties': {'name': {'type': 'string', 'description': '저장된 이름'},
                                                               'file_available': {'type': 'boolean',
                                                                                  'description': '색인에 기록한 원본 파일의 '
                                                                                                 '존재 여부입니다.'}},
                                                'description': '선택한 다이어그램 자산의 정보입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'list_diagram_assets': {'type': 'object',
                         'properties': {'library_id': {'type': 'string',
                                                       'description': 'include_ids=true에서 유지되는 라이브러리 구분자'},
                                        'assets': {'type': 'array',
                                                   'items': {'type': 'object'},
                                                   'description': '다이어그램 자산과 요청한 속성입니다.'},
                                        'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                        'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                        'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                        'next_offset': {'description': '다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.',
                                                        'type': ['integer', 'null']},
                                        'purpose': {'type': 'string', 'description': '이 라이브러리의 용도입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'place_diagram_asset': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'asset_id': {'type': 'string', 'description': '자산 ID'},
                                        'object_guid': {'type': 'string',
                                                        'description': '삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 '
                                                                       '입력에 재사용'},
                                        'definition_created': {'type': 'boolean',
                                                               'description': '새 블록 정의를 생성했는지 나타냅니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'search_diagram_assets': {'type': 'object',
                           'properties': {'assets': {'type': 'array',
                                                     'items': {'type': 'object'},
                                                     'description': '검색된 다이어그램 자산과 요청한 속성입니다.'},
                                          'total': {'type': 'integer', 'description': '필터에 일치하는 전체 항목 수'},
                                          'offset': {'type': 'integer', 'description': '현재 페이지 시작 위치'},
                                          'limit': {'type': 'integer', 'description': '페이지 최대 항목 수'},
                                          'next_offset': {'description': '다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.',
                                                          'type': ['integer', 'null']},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'}}},
 'apply_drawing_style': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'recipe_id': {'type': 'string', 'description': '도면 레시피 ID입니다.'},
                                        'layers': {'type': 'array',
                                                   'items': {'type': 'object',
                                                             'properties': {'path': {'type': 'string',
                                                                                     'description': 'get_objects의 '
                                                                                                    'layer_paths '
                                                                                                    '필터로 연결 가능'},
                                                                            'role': {'type': 'string',
                                                                                     'description': '레이어 역할입니다.'},
                                                                            'layer_index': {'type': 'integer',
                                                                                            'description': 'Rhino '
                                                                                                           '레이어 '
                                                                                                           '인덱스입니다.'},
                                                                            'plot_weight_mm': {'type': 'number',
                                                                                               'description': '출력 '
                                                                                                              '선 '
                                                                                                              '두께(mm)입니다.'},
                                                                            'linetype': {'type': 'string',
                                                                                         'description': '선 '
                                                                                                        '종류입니다.'}}},
                                                   'description': '스타일을 적용한 레이어입니다.'},
                                        'review_preparation': {'type': 'object',
                                                               'properties': {'status': {'type': 'string',
                                                                                         'description': '현재 처리의 '
                                                                                                        '상태입니다. '
                                                                                                        '오류이면 '
                                                                                                        'message와 '
                                                                                                        'error_code를 '
                                                                                                        '확인합니다.'},
                                                                              'message': {'type': 'string',
                                                                                          'description': '연결 '
                                                                                                         'Rhino '
                                                                                                         'PID·문서 '
                                                                                                         '경로에 맞는 '
                                                                                                         '파이프 확인 '
                                                                                                         '안내'},
                                                                              'cli': {'type': 'object',
                                                                                      'properties': {'program': {'type': 'string',
                                                                                                                 'description': '실행할 '
                                                                                                                                '프로그램입니다.'},
                                                                                                     'discovery_arguments': {'type': 'array',
                                                                                                                             'items': {'type': 'string'},
                                                                                                                             'description': '실행 '
                                                                                                                                            '환경 '
                                                                                                                                            '확인에 '
                                                                                                                                            '사용할 '
                                                                                                                                            '인수입니다.'},
                                                                                                     'arguments_template': {'type': 'array',
                                                                                                                            'items': {'type': 'string'},
                                                                                                                            'description': '검토 '
                                                                                                                                           '출력 '
                                                                                                                                           '명령의 '
                                                                                                                                           '인수 '
                                                                                                                                           '템플릿입니다.'}},
                                                                                      'description': '검토 출력에 사용할 '
                                                                                                     'CLI 실행 '
                                                                                                     '정보입니다.'}},
                                                               'description': 'A4 레시피에서 준비한 검토용 정보입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'get_drawing_recipe': {'type': 'object',
                        'properties': {'status': {'type': 'string',
                                                  'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                       'recipe': {'type': 'object',
                                                  'properties': {'name': {'type': 'string',
                                                                          'description': '이름입니다.'},
                                                                 'description': {'type': 'string',
                                                                                 'description': '레시피 자체의 설명 문자열'},
                                                                 'projection': {'type': 'object',
                                                                                'properties': {'type': {'type': 'string',
                                                                                                        'description': '투영 '
                                                                                                                       '방식입니다.'}},
                                                                                'description': '도면 투영 설정입니다.'}},
                                                  'description': '선택한 도면 레시피의 요약입니다.'},
                                       'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                       'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                       'next_step_guide': {'type': 'string',
                                                           'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                          '반환합니다.'}}},
 'get_plan_section_result': {'type': 'object',
                             'properties': {'status': {'type': 'string',
                                                       'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                      '확인합니다.'},
                                            'result_id': {'type': 'string',
                                                          'description': '같은 Rhino 문서 인스턴스에 보관된 결과 ID입니다.'},
                                            'offset': {'type': 'integer',
                                                       'description': '결과 문자열의 UTF-16 코드 단위 시작 위치입니다.'},
                                            'json_chunk': {'type': 'string',
                                                           'description': '전체 객체가 아니라 JSON 문자열 조각'},
                                            'total_characters': {'type': 'integer',
                                                                 'description': 'UTF-16 코드 단위 길이'},
                                            'next_offset': {'description': '이어 읽을 UTF-16 코드 단위 위치입니다. null이면 마지막 '
                                                                           '페이지입니다.',
                                                            'type': ['integer', 'null']},
                                            'result_sha256': {'type': 'string',
                                                              'description': '보관된 전체 결과 문자열의 SHA-256 해시입니다.'},
                                            'observation': {'type': 'string',
                                                            'description': '보관된 실행 결과의 관찰 시점에 대한 안내입니다.'},
                                            'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                            'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                            'next_step_guide': {'type': 'string',
                                                                'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                               '경우에만 반환합니다.'}}},
 'import_drawing_hatch_patterns': {'type': 'object',
                                   'properties': {'status': {'type': 'string',
                                                             'description': '현재 처리의 상태입니다. 오류이면 message와 '
                                                                            'error_code를 확인합니다.'},
                                                  'patterns': {'type': 'array',
                                                               'items': {'type': 'string'},
                                                               'description': '신규뿐 아니라 기존에 있어 사용 가능한 패턴 이름도 포함'},
                                                  'message': {'type': 'string',
                                                              'description': '현재 결과 또는 오류의 설명입니다.'},
                                                  'error_trace': {'description': '오류 진단 정보입니다.'},
                                                  'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                                  'next_step_guide': {'type': 'string',
                                                                      'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. '
                                                                                     '필요한 경우에만 반환합니다.'}}},
 'list_drawing_recipes': {'type': 'object',
                          'properties': {'total': {'type': 'integer', 'description': '조회된 레시피 수입니다.'},
                                         'recipes': {'type': 'array',
                                                     'items': {'type': 'object',
                                                               'properties': {'recipe_id': {'type': 'string',
                                                                                            'description': 'get_drawing_recipe '
                                                                                                           '/ '
                                                                                                           'apply_drawing_style에 '
                                                                                                           '재사용'},
                                                                              'name': {'type': ['string', 'null'],
                                                                                       'description': '이름입니다.'},
                                                                              'description': {'type': ['string',
                                                                                                       'null'],
                                                                                              'description': '설명입니다.'},
                                                                              'projection': {'type': ['string',
                                                                                                      'null'],
                                                                                             'description': '투영 '
                                                                                                            '방식입니다.'},
                                                                              'recommended_scales': {'type': 'array',
                                                                                                     'items': {'type': 'string'},
                                                                                                     'description': '권장 '
                                                                                                                    '축척의 '
                                                                                                                    '분모 '
                                                                                                                    '목록입니다.'}}},
                                                     'description': '도면 레시피와 요청한 속성입니다.'},
                                         'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                         'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                         'next_step_guide': {'type': 'string',
                                                             'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                            '반환합니다.'}}},
 'plan_section': {'type': 'object',
                  'properties': {'status': {'type': 'string',
                                            'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                 'drawing_status': {'type': 'string', 'description': '생성된 도면의 상태입니다.'},
                                 'result': {'type': 'object',
                                            'properties': {'status': {'type': 'string',
                                                                      'description': '현재 처리의 상태입니다. 오류이면 message와 '
                                                                                     'error_code를 확인합니다.'},
                                                           'requested': {'type': 'integer',
                                                                         'description': '요청한 대상 수입니다.'},
                                                           'completed': {'type': 'integer',
                                                                         'description': '도면 생성을 완료한 대상 수입니다.'},
                                                           'output': {'type': 'string',
                                                                      'description': '실행 중 기록한 출력 문자열입니다.'},
                                                           'result_delivery': {'type': 'string',
                                                                               'description': '전체 결과 또는 페이지 조회 '
                                                                                              '방식입니다.'},
                                                           'result_id': {'type': 'string',
                                                                         'description': 'get_plan_section_result로 '
                                                                                        '복구'},
                                                           'result_characters': {'type': 'integer',
                                                                                 'description': '전체 결과 문자열의 '
                                                                                                'UTF-16 코드 단위 '
                                                                                                '길이입니다.'},
                                                           'result_sha256': {'type': 'string',
                                                                             'description': '보관된 전체 결과 문자열의 '
                                                                                            'SHA-256 해시입니다.'},
                                                           'retention': {'type': 'string',
                                                                         'description': '동일 문서·Bridge, 최대 1시간·최신 '
                                                                                        '8개·총 64 MiB 보관 안내'}},
                                            'description': '단면 생성 결과입니다. 큰 결과에는 페이지 조회용 result_id가 포함됩니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'get_logic_by_id': {'type': 'object',
                     'properties': {'file_name': {'type': 'string', 'description': '파일명입니다.'},
                                    'components': {'type': 'array',
                                                   'items': {'type': 'object',
                                                             'properties': {'name': {'type': 'string',
                                                                                     'description': '이름입니다.'},
                                                                            'category': {'type': 'string',
                                                                                         'description': '분류입니다.'},
                                                                            'descriptions': {'type': 'array',
                                                                                             'items': {'type': 'string'},
                                                                                             'description': '컴포넌트에 '
                                                                                                            '기록된 '
                                                                                                            '설명입니다.'}}},
                                                   'description': '정의에 사용한 컴포넌트입니다.'},
                                    'all_descriptions': {'type': 'array',
                                                         'items': {'type': 'string'},
                                                         'description': '정의에서 수집한 설명 목록입니다.'},
                                    'metadata': {'type': 'object',
                                                 'properties': {},
                                                 'description': '정의 파일에서 읽은 메타데이터입니다.'},
                                    'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                    'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                    'next_step_guide': {'type': 'string',
                                                        'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                       '반환합니다.'}}},
 'list_capsules': {'type': 'object',
                   'properties': {'total': {'type': 'integer', 'description': '조회 조건에 맞는 전체 항목 수입니다.'},
                                  'offset': {'type': 'integer', 'description': '이번 페이지의 시작 위치입니다.'},
                                  'limit': {'type': 'integer', 'description': '이번 응답의 최대 항목 수입니다.'},
                                  'next_offset': {'description': '다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.',
                                                  'type': ['integer', 'null']},
                                  'capsules': {'type': 'array',
                                               'items': {'type': 'object',
                                                         'properties': {'capsule_id': {'type': 'string',
                                                                                       'description': 'audited=true일 '
                                                                                                      '때 '
                                                                                                      'run_gh_definition에 '
                                                                                                      '사용 가능'},
                                                                        'capability': {'type': 'string',
                                                                                       'description': '캡슐의 '
                                                                                                      '기능입니다.'},
                                                                        'structure_type': {'type': 'string',
                                                                                           'description': '구조 '
                                                                                                          '유형입니다.'},
                                                                        'definition_file': {'type': 'string',
                                                                                            'description': '경로·확장자를 '
                                                                                                           '뺀 로컬 '
                                                                                                           '이름 → '
                                                                                                           'get_logic_by_id'},
                                                                        'title': {'type': 'string',
                                                                                  'description': '제목입니다.'},
                                                                        'audited': {'type': 'boolean',
                                                                                    'description': '실행 허용 검사를 '
                                                                                                   '통과했는지 나타냅니다.'},
                                                                        'inputs': {'type': 'array',
                                                                                   'items': {'type': 'string'},
                                                                                   'description': '캡슐 입력 포트 '
                                                                                                  '이름입니다. 세부 계약은 '
                                                                                                  '정의에서 확인합니다.'},
                                                                        'outputs': {'type': 'array',
                                                                                    'items': {'type': 'string'},
                                                                                    'description': '출력 포트 이름 '
                                                                                                   '목록입니다.'}}},
                                               'description': '실행 캡슐과 요청한 포트·정의 정보입니다.'},
                                  'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                  'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                  'next_step_guide': {'type': 'string',
                                                      'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                     '반환합니다.'}}},
 'list_library': {'type': 'object',
                  'properties': {'total_entries': {'type': 'integer', 'description': '라이브러리 전체 항목 수입니다.'},
                                 'logic_names': {'type': 'array',
                                                 'items': {'type': 'string'},
                                                 'description': '기본 응답에서도 get_logic_by_id.logic_id로 사용 가능'},
                                 'logic_count': {'type': 'number',
                                                 'description': 'include_ids=false에서 logic_ids 대신 추가됨'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'run_gh_definition': {'type': 'object',
                       'properties': {'status': {'type': 'string',
                                                 'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                      'capsule_id': {'type': 'string', 'description': '실행한 캡슐 ID입니다.'},
                                      'outputs': {'type': 'object',
                                                  'properties': {},
                                                  'description': '출력 포트별 값입니다. 의미·타입·단위는 캡슐 계약에 따릅니다.'},
                                      'baked_guids': {'type': 'array',
                                                      'items': {'type': 'string'},
                                                      'description': '생성 객체 관찰·캡처에 재사용'},
                                      'analysis_method': {'type': 'string', 'description': '해석 방식입니다.'},
                                      'confidence': {'type': 'string',
                                                     'description': '매니페스트 선언: api/high, template/medium, '
                                                                    'rule_based/low'},
                                      'warnings': {'type': 'array',
                                                   'items': {'type': 'string'},
                                                   'description': '결과를 해석할 때 확인할 경고입니다.'},
                                      'error': {'description': '오류 내용입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'get_construction_guidance': {'type': 'object',
                               'properties': {'total': {'type': 'integer', 'description': '조회 조건에 맞는 전체 항목 수입니다.'},
                                              'source': {'type': 'string', 'description': '예비 치수 산정용 라이브러리 출처'},
                                              'systems': {'type': 'array',
                                                          'items': {'type': 'object',
                                                                    'properties': {'system_id': {'type': 'string',
                                                                                                 'description': 'typology의 '
                                                                                                                'construction_system '
                                                                                                                '또는 '
                                                                                                                '재료 '
                                                                                                                '메타데이터로 '
                                                                                                                '연결'},
                                                                                   'name': {'type': 'string',
                                                                                            'description': '이름입니다.'},
                                                                                   'category': {'type': 'string',
                                                                                                'description': '분류입니다.'},
                                                                                   'structural_material': {'type': 'string',
                                                                                                           'description': '구조 '
                                                                                                                          '재료입니다.'},
                                                                                   'fits_span': {'type': 'boolean',
                                                                                                 'description': '입력 '
                                                                                                                'span_m과 '
                                                                                                                '경험칙 '
                                                                                                                '범위 '
                                                                                                                '비교이지 '
                                                                                                                '내력 '
                                                                                                                '판정이 '
                                                                                                                '아님'},
                                                                                   'depth_guidance': {'type': 'array',
                                                                                                      'items': {'type': 'object',
                                                                                                                'properties': {'element': {'type': 'string',
                                                                                                                                           'description': '부재 '
                                                                                                                                                          '종류입니다.'},
                                                                                                                               'suggested_depth_mm': {'type': 'number',
                                                                                                                                                      'description': '계산한 '
                                                                                                                                                                     '권장 '
                                                                                                                                                                     '부재 '
                                                                                                                                                                     '깊이(mm)입니다.'},
                                                                                                                               'rule': {'type': 'string',
                                                                                                                                        'description': '부재 '
                                                                                                                                                       '깊이를 '
                                                                                                                                                       '계산한 '
                                                                                                                                                       '스팬 '
                                                                                                                                                       '비율입니다.'}}},
                                                                                                      'description': '입력 '
                                                                                                                     '스팬과 '
                                                                                                                     '경험칙으로 '
                                                                                                                     '계산한 '
                                                                                                                     '부재 '
                                                                                                                     '깊이입니다.'},
                                                                                   'construction_detail': {'type': 'string',
                                                                                                           'description': '구법 '
                                                                                                                          '이름입니다.'},
                                                                                   'construction_reference': {'type': 'object',
                                                                                                              'properties': {'kind': {'type': 'string',
                                                                                                                                      'description': '참조 '
                                                                                                                                                     '종류입니다. '
                                                                                                                                                     'construction_system은 '
                                                                                                                                                     '구조 '
                                                                                                                                                     '시스템입니다.'},
                                                                                                                             'id': {'type': 'string',
                                                                                                                                    'description': '참조할 '
                                                                                                                                                   '구조 '
                                                                                                                                                   '시스템 '
                                                                                                                                                   'ID입니다.'}},
                                                                                                              'description': '구법 '
                                                                                                                             '참조를 '
                                                                                                                             '기록할 '
                                                                                                                             '종류와 '
                                                                                                                             'ID입니다.'},
                                                                                   'render_material_ids': {'type': 'array',
                                                                                                           'items': {'type': 'string'},
                                                                                                           'description': '의도한 '
                                                                                                                          '유효 '
                                                                                                                          '재료 '
                                                                                                                          '하나를 '
                                                                                                                          'assign_material에 '
                                                                                                                          '선택'}}},
                                                          'description': '검색한 구조 시스템과 요청한 경험칙·재료 정보입니다.'},
                                              'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                              'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                              'next_step_guide': {'type': 'string',
                                                                  'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                 '경우에만 반환합니다.'}}},
 'get_typology_narrative': {'type': 'object',
                            'properties': {'total': {'type': 'integer', 'description': 'limit를 적용하기 전 전체 일치 수'},
                                           'entries': {'type': 'array',
                                                       'items': {'type': 'object',
                                                                 'properties': {'typology_id': {'type': 'string',
                                                                                                'description': '건축 '
                                                                                                               '유형 '
                                                                                                               'ID입니다.'},
                                                                                'name': {'type': 'string',
                                                                                         'description': '이름입니다.'},
                                                                                'era': {'type': 'string',
                                                                                        'description': '시대입니다.'},
                                                                                'region': {'type': 'string',
                                                                                           'description': '지역입니다.'},
                                                                                'narrative': {'type': 'string',
                                                                                              'description': '유형의 '
                                                                                                             '배경과 '
                                                                                                             '특징입니다.'},
                                                                                'urban_role': {'type': 'string',
                                                                                               'description': '도시에서의 '
                                                                                                              '역할입니다.'},
                                                                                'related_construction_systems': {'type': 'array',
                                                                                                                 'items': {'type': 'string'},
                                                                                                                 'description': 'get_construction_guidance의 '
                                                                                                                                'query로 '
                                                                                                                                '검색 '
                                                                                                                                '가능'}}},
                                                       'description': '검색된 유형 설명과 요청한 속성입니다.'},
                                           'source': {'type': 'string', 'description': '자료 출처입니다.'},
                                           'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                           'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                           'next_step_guide': {'type': 'string',
                                                               'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                              '반환합니다.'}}},
 'search_detail_sources': {'type': 'object',
                           'properties': {'status': {'type': 'string',
                                                     'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                    '확인합니다.'},
                                          'query': {'type': 'string', 'description': '검색어입니다.'},
                                          'query_terms': {'type': 'array',
                                                          'items': {'type': 'string'},
                                                          'description': '원래 검색어에서 추출한 단어입니다.'},
                                          'expanded_terms': {'type': 'array',
                                                             'items': {},
                                                             'description': '검색에 추가한 관련 단어입니다.'},
                                          'sources': {'type': 'array',
                                                      'items': {'type': 'object',
                                                                'properties': {'source_id': {'type': 'string',
                                                                                             'description': '출처 '
                                                                                                            'ID입니다.'},
                                                                               'title': {'type': 'string',
                                                                                         'description': '제목입니다.'},
                                                                               'url': {'type': 'string',
                                                                                       'description': '자료 출처의 웹 '
                                                                                                      '주소입니다.'},
                                                                               'terms_url': {'type': 'string',
                                                                                             'description': '자료 '
                                                                                                            '이용 '
                                                                                                            '조건의 '
                                                                                                            '웹 '
                                                                                                            '주소입니다.'},
                                                                               'formats': {'type': 'array',
                                                                                           'items': {'type': 'string'},
                                                                                           'description': '제공하는 '
                                                                                                          '자료 '
                                                                                                          '형식입니다.'},
                                                                               'access': {'type': 'string',
                                                                                          'description': '자료 접근 '
                                                                                                         '조건입니다.'},
                                                                               'redistribution': {'type': 'string',
                                                                                                  'description': '자료 '
                                                                                                                 '재배포 '
                                                                                                                 '조건입니다.'},
                                                                               'generation_use': {'type': 'string',
                                                                                                  'description': '생성 '
                                                                                                                 '작업에서의 '
                                                                                                                 '이용 '
                                                                                                                 '조건입니다.'},
                                                                               'matched_terms': {'type': 'array',
                                                                                                 'items': {'type': 'string'},
                                                                                                 'description': '일치한 '
                                                                                                                '검색 '
                                                                                                                '단어입니다.'}}},
                                                      'description': '조건에 일치하는 상세 자료 출처입니다.'},
                                          'scope': {'type': 'string', 'description': '검색한 출처 디렉터리의 범위입니다.'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'}}},
 'check_egress': {'type': 'object',
                  'properties': {'passed': {'type': 'boolean',
                                            'description': '실제 수행한 검사만 합산. 빠진 경로 검사를 통과한 것이 아님'},
                                 'occupancy': {'type': 'string', 'description': '건물 용도입니다.'},
                                 'occupant_load': {'type': 'integer',
                                                   'description': '면적과 용도별 1인당 면적으로 계산해 올림한 재실 인원입니다.'},
                                 'area_m2': {'type': 'number', 'description': '입력한 면적(m²)입니다.'},
                                 'gross_area_m2': {'type': 'number',
                                                   'description': '경계 직사각형 면적이지 불규칙 바닥의 실측 면적은 아님'},
                                 'checks': {'type': 'array',
                                            'items': {'type': 'object',
                                                      'properties': {'check': {'type': 'string',
                                                                               'description': '검사 항목 이름입니다.'},
                                                                     'required': {'type': 'number',
                                                                                  'description': '검사 항목에서 요구하는 '
                                                                                                 '최소값입니다.'},
                                                                     'provided': {'type': 'number',
                                                                                  'description': '현재 입력에서 제공한 '
                                                                                                 '값입니다.'},
                                                                     'passed': {'type': 'boolean',
                                                                                'description': '이 항목이 비교 기준을 '
                                                                                               '충족했는지 나타냅니다.'},
                                                                     'basis': {'type': 'string',
                                                                               'description': '해당 비교의 근거'}}},
                                            'description': '수행한 항목별 검사 결과입니다.'},
                                 'warnings': {'type': 'array',
                                              'items': {'type': 'string'},
                                              'description': '결과를 해석할 때 확인할 경고입니다.'},
                                 'source_note': {'type': 'string', 'description': '계산 기준의 출처와 적용 범위입니다.'},
                                 'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                 'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                 'next_step_guide': {'type': 'string',
                                                     'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.'}}},
 'export_structural_report': {'type': 'object',
                              'properties': {'status': {'type': 'string',
                                                        'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                       '확인합니다.'},
                                             'path': {'type': 'string', 'description': '작성된 Markdown 파일'},
                                             'runs': {'type': 'integer', 'description': '실제 포함한 저장 실행 수'},
                                             'latest_method': {'type': 'string', 'description': '가장 최근 저장된 실행 방식'},
                                             'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                             'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                             'next_step_guide': {'type': 'string',
                                                                 'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                '경우에만 반환합니다.'}}},
 'list_design_codes': {'type': 'object',
                       'properties': {'default': {'type': 'string', 'description': '기본 설계 기준 ID입니다.'},
                                      'profiles': {'type': 'array',
                                                   'items': {'type': 'object',
                                                             'properties': {'id': {'type': 'string',
                                                                                   'description': 'validate_structure '
                                                                                                  '/ '
                                                                                                  'visualize_structure의 '
                                                                                                  'design_code에 '
                                                                                                  '사용'},
                                                                            'name': {'type': 'string',
                                                                                     'description': '이름입니다.'},
                                                                            'basis': {'type': 'string',
                                                                                      'description': '기준의 근거입니다.'},
                                                                            'verified': {'type': 'boolean',
                                                                                         'description': '프로필 값 '
                                                                                                        '검증이며 '
                                                                                                        '프로젝트의 법규 '
                                                                                                        '준수/구조 '
                                                                                                        '승인과 다름'},
                                                                            'unverified': {'type': 'array',
                                                                                           'items': {},
                                                                                           'description': '검증되지 '
                                                                                                          '않은 '
                                                                                                          '매개변수 '
                                                                                                          '목록입니다.'},
                                                                            'deflection_limit_ratio': {'type': 'number',
                                                                                                       'description': '허용 '
                                                                                                                      '처짐 '
                                                                                                                      'L/n의 '
                                                                                                                      '분모 '
                                                                                                                      'n입니다.'},
                                                                            'imposed_floor_kn_m2': {'type': 'object',
                                                                                                    'properties': {},
                                                                                                    'description': '프로필의 '
                                                                                                                   '권장 '
                                                                                                                   '바닥 '
                                                                                                                   '활하중입니다. '
                                                                                                                   '단위는 '
                                                                                                                   'kN/m²입니다.'}}},
                                                   'description': '설계 기준 프로필과 요청한 매개변수입니다.'},
                                      'problems': {'type': 'array',
                                                   'items': {},
                                                   'description': '로딩 중 거부된 사용자 프로필 문제'},
                                      'user_dir': {'type': 'string', 'description': '사용자 설계 기준 프로필 폴더입니다.'},
                                      'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                      'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                      'next_step_guide': {'type': 'string',
                                                          'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                         '반환합니다.'}}},
 'validate_structure': {'type': 'object',
                        'properties': {'status': {'type': 'string',
                                                  'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.'},
                                       'passed': {'type': ['boolean', 'null'],
                                                  'description': 'indicative인 경우 null 가능. 구조 안전 인증을 뜻하지 않음'},
                                       'structure_type': {'type': 'string', 'description': '구조 유형입니다.'},
                                       'material': {'type': 'string', 'description': '재료입니다.'},
                                       'confidence': {'type': 'string', 'description': '경고·가정·미검증 값과 함께 해석'},
                                       'results': {'type': 'object',
                                                   'properties': {'analysis_method': {'type': 'string',
                                                                                      'description': '해석 방식입니다.'},
                                                                  'max_deflection_mm': {'type': 'number',
                                                                                        'description': '최대 '
                                                                                                       '처짐(mm)입니다.'},
                                                                  'deflection_limit_mm': {'type': 'number',
                                                                                          'description': '허용 '
                                                                                                         '처짐(mm)입니다.'},
                                                                  'span_m': {'type': 'number',
                                                                             'description': '검토 스팬(m)입니다.'},
                                                                  'utilization_ratio': {'type': 'number',
                                                                                        'description': '기준 대비 '
                                                                                                       '사용률입니다.'},
                                                                  'per_element_utilization': {'type': 'array',
                                                                                              'items': {'type': 'object',
                                                                                                        'properties': {'source_guids': {'type': 'array',
                                                                                                                                        'items': {'type': 'string'},
                                                                                                                                        'description': '표시 '
                                                                                                                                                       '대상 '
                                                                                                                                                       'display_guids로 '
                                                                                                                                                       '재사용 '
                                                                                                                                                       '가능'},
                                                                                                                       'utilization': {'type': 'number',
                                                                                                                                       'description': '부재 '
                                                                                                                                                      '사용률입니다.'},
                                                                                                                       'combination': {'type': 'string',
                                                                                                                                       'description': '지배 '
                                                                                                                                                      '하중 '
                                                                                                                                                      '조합입니다.'}}},
                                                                                              'description': '부재별 '
                                                                                                             '검토 '
                                                                                                             '결과와 '
                                                                                                             '사용률입니다.'}},
                                                   'description': '구조 검토의 수치와 부재별 결과입니다.'},
                                       'worst_member_guids': {'type': 'array',
                                                              'items': {'type': 'string'},
                                                              'description': '상위 최대 5개, 전체 해석 범위 아님'},
                                       'warnings': {'type': 'array',
                                                    'items': {'type': 'string'},
                                                    'description': '결과를 해석할 때 확인할 경고입니다.'},
                                       'assumptions': {'type': 'array',
                                                       'items': {'type': 'string'},
                                                       'description': '검토에 사용한 가정입니다.'},
                                       'design_code': {'type': 'object',
                                                       'properties': {'id': {'type': 'string',
                                                                             'description': '검토에 사용한 설계 기준 '
                                                                                            'ID입니다.'},
                                                                      'unverified': {'type': 'array',
                                                                                     'items': {},
                                                                                     'description': '검증되지 않은 매개변수 '
                                                                                                    '목록입니다.'}},
                                                       'description': '검토에 사용한 설계 기준 프로필입니다.'},
                                       'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                       'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                       'next_step_guide': {'type': 'string',
                                                           'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                          '반환합니다.'}}},
 'visualize_structure': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'analysis_method': {'type': 'string', 'description': '해석 방식입니다.'},
                                        'max_displacement_mm': {'type': 'number', 'description': '최대 변위(mm)입니다.'},
                                        'deflection_limit_mm': {'type': 'number', 'description': '허용 처짐(mm)입니다.'},
                                        'span_m': {'type': 'number', 'description': '검토 스팬(m)입니다.'},
                                        'max_utilization': {'type': 'number', 'description': '최대 부재 사용률입니다.'},
                                        'scale': {'type': 'number', 'description': '실제 변위가 아닌 표시 과장 배율'},
                                        'elements': {'type': 'array',
                                                     'items': {'type': 'object',
                                                               'properties': {'source_guids': {'type': 'array',
                                                                                               'items': {'type': 'string'},
                                                                                               'description': 'display_guids '
                                                                                                              '또는 '
                                                                                                              '객체 '
                                                                                                              '관찰에 '
                                                                                                              '재사용'},
                                                                              'max_displacement_mm': {'type': 'number',
                                                                                                      'description': '최대 '
                                                                                                                     '변위(mm)입니다.'},
                                                                              'utilization': {'type': 'number',
                                                                                              'description': '부재 '
                                                                                                             '사용률입니다.'}}},
                                                     'description': '시각화한 부재별 결과입니다.'},
                                        'nodes': {'type': 'integer', 'description': '해석 노드 수입니다.'},
                                        'warnings': {'type': 'array',
                                                     'items': {'type': 'string'},
                                                     'description': '결과를 해석할 때 확인할 경고입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}},
 'export_asset_contract': {'type': 'object',
                           'properties': {'status': {'type': 'string',
                                                     'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                    '확인합니다.'},
                                          'asset_id': {'type': 'string', 'description': '자산 ID입니다.'},
                                          'glb_path': {'type': 'string', 'description': '내보낸 GLB 파일 경로입니다.'},
                                          'contract_path': {'type': 'string',
                                                            'description': 'import_asset_contract에 전달'},
                                          'dimensions_mm': {'type': 'object',
                                                            'properties': {'width': {'type': 'number',
                                                                                     'description': '너비(mm)입니다.'},
                                                                           'depth': {'type': 'number',
                                                                                     'description': '깊이(mm)입니다.'},
                                                                           'height': {'type': 'number',
                                                                                      'description': '높이(mm)입니다.'}},
                                                            'description': '내보낸 자산의 경계 치수입니다. 단위는 mm입니다.'},
                                          'materials': {'type': 'array',
                                                        'items': {},
                                                        'description': '인식된 Almond 재료 그룹. 비어 있어도 모든 재료가 보존됐다는 뜻은 '
                                                                       '아님'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'}}},
 'get_blender_helper_script': {'type': 'object',
                               'properties': {'status': {'type': 'string',
                                                         'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                        '확인합니다.'},
                                              'action': {'type': 'string', 'description': '스크립트의 작업 종류입니다.'},
                                              'script': {'type': 'string',
                                                         'description': 'Blender에서 실행할 Python 코드입니다.'},
                                              'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                              'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                              'next_step_guide': {'type': 'string',
                                                                  'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                 '경우에만 반환합니다.'}}},
 'import_asset_contract': {'type': 'object',
                           'properties': {'status': {'type': 'string',
                                                     'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                    '확인합니다.'},
                                          'asset_id': {'type': 'string', 'description': '자산 ID입니다.'},
                                          'source_app': {'type': 'string', 'description': '자산을 내보낸 앱입니다.'},
                                          'imported_count': {'type': 'integer', 'description': '가져온 객체 수입니다.'},
                                          'imported_guids': {'type': 'array',
                                                             'items': {'type': 'string'},
                                                             'description': '객체 관찰·캡처·재료 보정에 재사용'},
                                          'metadata_restored': {'type': 'integer',
                                                                'description': '메타데이터를 기록한 객체 수'},
                                          'materials_deduplicated': {'type': 'integer',
                                                                     'description': '중복 제거한 재료 수입니다.'},
                                          'unknown_material_ids': {'type': 'array',
                                                                   'items': {},
                                                                   'description': 'Almond 라이브러리에서 찾지 못한 재료 '
                                                                                  'ID입니다.'},
                                          'dimension_check': {'type': 'object',
                                                              'properties': {'status': {'type': 'string',
                                                                                        'description': '가져온 자산의 '
                                                                                                       '치수 비교 '
                                                                                                       '결과입니다.'},
                                                                             'expected_sorted_mm': {'type': 'array',
                                                                                                    'items': {'type': 'number'},
                                                                                                    'description': '크기순으로 '
                                                                                                                   '정렬한 '
                                                                                                                   '원본 '
                                                                                                                   '경계 '
                                                                                                                   '치수(mm)입니다.'},
                                                                             'measured_sorted_mm': {'type': 'array',
                                                                                                    'items': {'type': 'number'},
                                                                                                    'description': '크기순으로 '
                                                                                                                   '정렬한 '
                                                                                                                   '가져온 '
                                                                                                                   '객체의 '
                                                                                                                   '경계 '
                                                                                                                   '치수(mm)입니다.'},
                                                                             'worst_relative_error': {'type': 'number',
                                                                                                      'description': '축별 '
                                                                                                                     '상대 '
                                                                                                                     '오차 '
                                                                                                                     '중 '
                                                                                                                     '최대값입니다.'},
                                                                             'tolerance': {'type': 'number',
                                                                                           'description': '허용 상대 '
                                                                                                          '오차입니다. '
                                                                                                          '크기 순으로 '
                                                                                                          '정렬한 축별 '
                                                                                                          '치수를 '
                                                                                                          '비교합니다.'}},
                                                              'description': '내보내기 전후의 경계 치수 비교입니다.'},
                                          'layer': {'type': 'string', 'description': '가져온 객체의 레이어입니다.'},
                                          'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                          'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                          'next_step_guide': {'type': 'string',
                                                              'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                             '반환합니다.'}}},
 'publish_objects_to_chestnut': {'type': 'object',
                                 'properties': {'status': {'type': 'string',
                                                           'description': '현재 처리의 상태입니다. 오류이면 message와 '
                                                                          'error_code를 확인합니다.'},
                                                'success': {'type': 'boolean',
                                                            'description': '원격 /api/props/upsert 응답에서 온 값'},
                                                'chestnut_url': {'type': 'string',
                                                                 'description': '게시한 Chestnut 서비스의 주소입니다.'},
                                                'message': {'type': 'string',
                                                            'description': '현재 결과 또는 오류의 설명입니다.'},
                                                'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                                'next_step_guide': {'type': 'string',
                                                                    'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 '
                                                                                   '경우에만 반환합니다.'}}},
 'publish_to_chestnut': {'type': 'object',
                         'properties': {'status': {'type': 'string',
                                                   'description': '현재 처리의 상태입니다. 오류이면 message와 error_code를 '
                                                                  '확인합니다.'},
                                        'success': {'type': 'boolean',
                                                    'description': '하위 publish_objects_to_chestnut의 원격 응답을 그대로 '
                                                                   '반환'},
                                        'chestnut_url': {'type': 'string',
                                                         'description': '게시한 Chestnut 서비스의 주소입니다.'},
                                        'message': {'type': 'string', 'description': '현재 결과 또는 오류의 설명입니다.'},
                                        'error_code': {'type': 'string', 'description': '오류 유형입니다.'},
                                        'next_step_guide': {'type': 'string',
                                                            'description': '이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 '
                                                                           '반환합니다.'}}}}

def public_output_schema(name: str, wrapped: bool = True) -> dict:
    contract = deepcopy(CONTRACTS[name])
    if not wrapped:
        return contract
    return {"type": "object", "properties": {"result": {
        "type": "string", "contentMediaType": "application/json", "contentSchema": contract,
    }}, "required": ["result"], "x-fastmcp-wrap-result": True}

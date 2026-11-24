# 현행 툴 선언

beyond와 CoS의 `tools/list`에서 읽은 설명 및 입출력 스키마다. 두 경로의 값이 같으면 한 번만 표시한다.

- CoS 선언 SHA-256: `64c16ebbd4d8f9a3752c9989728a0e137768e4009bd8f7f43c338c25a01a2be3`
- beyond 선언 SHA-256: `fafcbd4ecbea732caa5d1257bd1c353632c940de9d6cd0c58c09b3c51c7cb04d`

### 1. analysis_01-list_design_codes

**CoS · beyond**

```txt
구조 해석에 사용할 설계기준 프로필 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "parameters, source, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "parameters, source, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "default": {
            "description": "기본으로 적용되는 프로필 ID.",
            "type": "string"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "problems": {
            "description": "로딩 중 거절된 사용자 프로필의 문제.",
            "items": {},
            "type": "array"
          },
          "profiles": {
            "items": {
              "properties": {
                "basis": {
                  "type": "string"
                },
                "deflection_limit_ratio": {
                  "description": "허용 처짐 L/n의 n.",
                  "type": "number"
                },
                "id": {
                  "description": "analysis_02-validate_structure tool과 analysis_03-visualize_structure tool의 design_code에 전달.",
                  "type": "string"
                },
                "imposed_floor_kn_m2": {
                  "description": "프로필 권장 활하중.",
                  "properties": {},
                  "type": "object"
                },
                "name": {
                  "type": "string"
                },
                "unverified": {
                  "items": {},
                  "type": "array"
                },
                "verified": {
                  "description": "프로필 값의 검증 여부. 프로젝트 법규 준수나 구조 승인은 별도.",
                  "type": "boolean"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "user_dir": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 2. analysis_02-validate_structure

**CoS · beyond**

```txt
Rhino 구조 형상의 해석과 설계기준 검토. 실행 이력에는 요청 옵션, 실제 엔진·입력·결과를 보관. native는 내보낸 모델과 적용한 하중도 기록. 이전 이력에 기록되지 않은 옵션은 알 수 없음으로 표시.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "default": false,
      "description": "네이티브 해석에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 입력에 반영한 하중과 중복되지 않게 산정.",
      "type": "boolean"
    },
    "connections": {
      "default": "rigid",
      "description": "네이티브 접합 조건. \"rigid\"는 모든 접합부의 모멘트를 전달하고, \"simple\"은 보 단부의 강축 휨과 가새 단부의 양축 휨을 해제. 같은 선상으로 이어지는 부재와 기둥은 연속 유지. 일반 볼트 접합 강구조·목구조는 \"simple\"에 가깝고 강접합은 보 처짐을 과소평가할 수 있음. 곡선 User Text의 release 값(\"pinned\", \"pinned_start\", \"pinned_end\", \"rigid\") 우선.",
      "type": "string"
    },
    "design_basis": {
      "default": "en1990",
      "description": "네이티브 하중 조합. \"en1990\"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. \"unfactored\"는 Karamba와 같이 둘 다 G + Q 적용.",
      "type": "string"
    },
    "design_code": {
      "default": "eurocode",
      "description": "설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. \"eurocode\"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. \"off\"는 design_basis=\"unfactored\"와 같이 G + Q 적용.",
      "type": "string"
    },
    "detail": {
      "default": false,
      "description": "네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.",
      "type": "boolean"
    },
    "engine": {
      "default": "auto",
      "description": "auto, native, karamba 중 선택. auto는 선형 프레임에 native, 그 외에 Karamba 선택. karamba는 api → template → rule_based 순으로 시도. 실제 적용 방식은 analysis_method·warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "default": "cold_formed",
      "description": "강재 중공 단면(CHS/RHS)의 제작 방식. \"cold_formed\"는 EN 10219 좌굴 곡선 c, \"hot_finished\"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 \"hot_finished\" 사용.",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점.",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "description": "같은 바닥 구획의 구성층·마감 등 추가 고정하중.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "description": "네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.",
      "type": "number"
    },
    "guids": {
      "description": "현재 Rhino 문서의 해석 대상 객체 GUID.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "load_kn": {
      "default": 10.0,
      "description": "전체 부과하중. native는 자유 절점에 하향(-Z) 균등 분배. 바닥·자산 하중과 중복되지 않게 산정하고 필요 시 0 지정.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\".",
      "type": "string"
    },
    "self_weight": {
      "default": true,
      "type": "boolean"
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "네이티브 해석에서 부재가 여러 절점으로 분할된 경우 L/250을 적용할 전체 경간(예: 3.1 m 두 구간으로 그린 6.2 m 장선)."
    },
    "stability": {
      "default": "auto",
      "description": "\"auto\"는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 ±X·±Y 횡변위 초기 불완전성 φ = 1/200 × αh × αm(5.3.2) 적용. alpha_cr < 10이면 2차 P-Delta ULS 해석, alpha_cr ≤ 1이면 불안정으로 실패 처리. \"off\"는 초기 불완전성을 적용하지 않는 1차 해석.",
      "type": "string"
    },
    "structure_type": {
      "default": "beam",
      "description": "\"beam\" 단순 보 휨·처짐, \"truss\" 축력·좌굴, \"shell\" 셸 응력·변위, \"frame\" 프레임 모멘트·전단, \"canopy\" 캔틸레버 캐노피, \"gridshell\" 대변형 그리드셸, \"membrane\" 막 구조 형상 탐색, \"highrise\" 고층 구조 시스템.",
      "type": "string"
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\". \"6.10ab\"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환."
    }
  },
  "required": [
    "guids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "default": false,
      "description": "네이티브 해석에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 입력에 반영한 하중과 중복되지 않게 산정.",
      "type": "boolean"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "connections": {
      "default": "rigid",
      "description": "네이티브 접합 조건. \"rigid\"는 모든 접합부의 모멘트를 전달하고, \"simple\"은 보 단부의 강축 휨과 가새 단부의 양축 휨을 해제. 같은 선상으로 이어지는 부재와 기둥은 연속 유지. 일반 볼트 접합 강구조·목구조는 \"simple\"에 가깝고 강접합은 보 처짐을 과소평가할 수 있음. 곡선 User Text의 release 값(\"pinned\", \"pinned_start\", \"pinned_end\", \"rigid\") 우선.",
      "type": "string"
    },
    "design_basis": {
      "default": "en1990",
      "description": "네이티브 하중 조합. \"en1990\"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. \"unfactored\"는 Karamba와 같이 둘 다 G + Q 적용.",
      "type": "string"
    },
    "design_code": {
      "default": "eurocode",
      "description": "설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. \"eurocode\"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. \"off\"는 design_basis=\"unfactored\"와 같이 G + Q 적용.",
      "type": "string"
    },
    "detail": {
      "default": false,
      "description": "네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.",
      "type": "boolean"
    },
    "engine": {
      "default": "auto",
      "description": "auto, native, karamba 중 선택. auto는 선형 프레임에 native, 그 외에 Karamba 선택. karamba는 api → template → rule_based 순으로 시도. 실제 적용 방식은 analysis_method·warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "default": "cold_formed",
      "description": "강재 중공 단면(CHS/RHS)의 제작 방식. \"cold_formed\"는 EN 10219 좌굴 곡선 c, \"hot_finished\"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 \"hot_finished\" 사용.",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점.",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "description": "같은 바닥 구획의 구성층·마감 등 추가 고정하중.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "description": "네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.",
      "type": "number"
    },
    "guids": {
      "description": "현재 Rhino 문서의 해석 대상 객체 GUID.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "load_kn": {
      "default": 10.0,
      "description": "전체 부과하중. native는 자유 절점에 하향(-Z) 균등 분배. 바닥·자산 하중과 중복되지 않게 산정하고 필요 시 0 지정.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\".",
      "type": "string"
    },
    "self_weight": {
      "default": true,
      "type": "boolean"
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "네이티브 해석에서 부재가 여러 절점으로 분할된 경우 L/250을 적용할 전체 경간(예: 3.1 m 두 구간으로 그린 6.2 m 장선)."
    },
    "stability": {
      "default": "auto",
      "description": "\"auto\"는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 ±X·±Y 횡변위 초기 불완전성 φ = 1/200 × αh × αm(5.3.2) 적용. alpha_cr < 10이면 2차 P-Delta ULS 해석, alpha_cr ≤ 1이면 불안정으로 실패 처리. \"off\"는 초기 불완전성을 적용하지 않는 1차 해석.",
      "type": "string"
    },
    "structure_type": {
      "default": "beam",
      "description": "\"beam\" 단순 보 휨·처짐, \"truss\" 축력·좌굴, \"shell\" 셸 응력·변위, \"frame\" 프레임 모멘트·전단, \"canopy\" 캔틸레버 캐노피, \"gridshell\" 대변형 그리드셸, \"membrane\" 막 구조 형상 탐색, \"highrise\" 고층 구조 시스템.",
      "type": "string"
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\". \"6.10ab\"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환."
    }
  },
  "required": [
    "guids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assumptions": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "confidence": {
            "description": "warnings·assumptions와 설계기준의 미검증 값까지 함께 검토.",
            "type": "string"
          },
          "design_code": {
            "properties": {
              "id": {
                "type": "string"
              },
              "unverified": {
                "items": {},
                "type": "array"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "material": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "passed": {
            "description": "indicative 해석에서는 판정이 없을 수 있음(null). 구조 안전 인증은 별도.",
            "type": [
              "boolean",
              "null"
            ]
          },
          "results": {
            "properties": {
              "analysis_method": {
                "type": "string"
              },
              "deflection_limit_mm": {
                "type": "number"
              },
              "max_deflection_mm": {
                "type": "number"
              },
              "per_element_utilization": {
                "items": {
                  "properties": {
                    "combination": {
                      "description": "부재 판정을 지배한 하중 조합.",
                      "type": "string"
                    },
                    "source_guids": {
                      "description": "analysis_03-visualize_structure tool의 display_guids에 재사용.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "utilization": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "span_m": {
                "type": "number"
              },
              "utilization_ratio": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          },
          "structure_type": {
            "type": "string"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "worst_member_guids": {
            "description": "검토 결과가 가장 불리한 부재 최대 5개.",
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 3. analysis_03-visualize_structure

**CoS · beyond**

```txt
구조 해석 결과를 임시 뷰포트 오버레이로 표시.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "default": false,
      "description": "네이티브 해석에서 analysis_02-validate_structure tool과 같은 배치 자산 하중을 추가하고 작용점에 하중 화살표 표시.",
      "type": "boolean"
    },
    "beam_diameter_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "원형 부재의 외경."
    },
    "beam_wall_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "clear": {
      "default": false,
      "description": "현재 해석 오버레이 제거.",
      "type": "boolean"
    },
    "color_by": {
      "default": "displacement",
      "description": "\"displacement\" 또는 \"utilization\".",
      "type": "string"
    },
    "connections": {
      "default": "rigid",
      "description": "analysis_02-validate_structure tool과 같은 \"rigid\" 또는 \"simple\". 핀 접합 단부는 작은 원으로 표시.",
      "type": "string"
    },
    "deflection_limit_ratio": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "허용 처짐 L/n의 n. 생략 시 설계기준 한계 사용(예: Eurocode의 L/250은 250)."
    },
    "design_basis": {
      "default": "en1990",
      "description": "네이티브 하중 조합. \"en1990\"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. \"unfactored\"는 Karamba와 같이 둘 다 G + Q 적용.",
      "type": "string"
    },
    "design_code": {
      "default": "eurocode",
      "description": "설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. \"eurocode\"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. \"off\"는 design_basis=\"unfactored\"와 같이 G + Q 적용.",
      "type": "string"
    },
    "display_guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "그릴 부재만 선택(예: 단면을 보여 줄 한 줄의 프레임). 해석은 guids 전체에 적용."
    },
    "engine": {
      "default": "auto",
      "description": "\"native\", \"karamba\", \"auto\". \"auto\"는 네이티브 프레임 솔버를 우선 사용하고 셸이 포함되거나 브리지에서 모델을 내보낼 수 없으면 Karamba 사용.",
      "type": "string"
    },
    "fabrication": {
      "default": "cold_formed",
      "description": "강재 중공 단면(CHS/RHS)의 제작 방식. \"cold_formed\"는 EN 10219 좌굴 곡선 c, \"hot_finished\"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 \"hot_finished\" 사용.",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점.",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "description": "같은 바닥 구획의 구성층·마감 등 추가 고정하중.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "description": "네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.",
      "type": "number"
    },
    "guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "구조 축선 곡선과 지점 표식 점의 GUID. 지점 표식이 없으면 최하단 절점을 지점으로 사용(fixed_supports 참조)."
    },
    "load_kn": {
      "default": 10.0,
      "description": "자유 절점에 하향(-Z) 균등 분배할 전체 부과하중.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\".",
      "type": "string"
    },
    "physics": {
      "default": true,
      "description": "false이면 해석 오버레이 없이 같은 부재의 일반 형상을 그려 전후 비교.",
      "type": "boolean"
    },
    "reanalyze": {
      "default": true,
      "description": "false이면 마지막 계산을 재사용하고 표시 옵션(scale, color_by, reveal, physics, title)만 갱신.",
      "type": "boolean"
    },
    "reveal": {
      "default": 1.0,
      "description": "표시할 부재 비율 0..1. 단계별 시공 재생에 사용.",
      "type": "number"
    },
    "scale": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정."
    },
    "self_weight": {
      "default": true,
      "type": "boolean"
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "처짐 한계 평가에 쓸 기준 경간. 생략 시 가장 긴 부재 사용. 6.2 m 장선을 3.1 m씩 분할했다면 6.2 지정."
    },
    "stability": {
      "default": "auto",
      "description": "analysis_02-validate_structure tool과 같은 \"auto\" 또는 \"off\".",
      "type": "string"
    },
    "title": {
      "default": "",
      "type": "string"
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\". \"6.10ab\"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환."
    },
    "view": {
      "default": "deflection",
      "description": "\"deflection\"은 처짐 형상, \"buckling\"은 지배 ULS 조합의 첫 좌굴 모드와 alpha_cr 표시(STABLE ≥ 10, SWAY-SENSITIVE 1~10, UNSTABLE ≤ 1).",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "default": false,
      "description": "네이티브 해석에서 analysis_02-validate_structure tool과 같은 배치 자산 하중을 추가하고 작용점에 하중 화살표 표시.",
      "type": "boolean"
    },
    "beam_diameter_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "원형 부재의 외경."
    },
    "beam_wall_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    },
    "clear": {
      "default": false,
      "description": "현재 해석 오버레이 제거.",
      "type": "boolean"
    },
    "color_by": {
      "default": "displacement",
      "description": "\"displacement\" 또는 \"utilization\".",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "connections": {
      "default": "rigid",
      "description": "analysis_02-validate_structure tool과 같은 \"rigid\" 또는 \"simple\". 핀 접합 단부는 작은 원으로 표시.",
      "type": "string"
    },
    "deflection_limit_ratio": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "허용 처짐 L/n의 n. 생략 시 설계기준 한계 사용(예: Eurocode의 L/250은 250)."
    },
    "design_basis": {
      "default": "en1990",
      "description": "네이티브 하중 조합. \"en1990\"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. \"unfactored\"는 Karamba와 같이 둘 다 G + Q 적용.",
      "type": "string"
    },
    "design_code": {
      "default": "eurocode",
      "description": "설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. \"eurocode\"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. \"off\"는 design_basis=\"unfactored\"와 같이 G + Q 적용.",
      "type": "string"
    },
    "display_guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "그릴 부재만 선택(예: 단면을 보여 줄 한 줄의 프레임). 해석은 guids 전체에 적용."
    },
    "engine": {
      "default": "auto",
      "description": "\"native\", \"karamba\", \"auto\". \"auto\"는 네이티브 프레임 솔버를 우선 사용하고 셸이 포함되거나 브리지에서 모델을 내보낼 수 없으면 Karamba 사용.",
      "type": "string"
    },
    "fabrication": {
      "default": "cold_formed",
      "description": "강재 중공 단면(CHS/RHS)의 제작 방식. \"cold_formed\"는 EN 10219 좌굴 곡선 c, \"hot_finished\"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 \"hot_finished\" 사용.",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점.",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "description": "같은 바닥 구획의 구성층·마감 등 추가 고정하중.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "description": "네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.",
      "type": "number"
    },
    "guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "구조 축선 곡선과 지점 표식 점의 GUID. 지점 표식이 없으면 최하단 절점을 지점으로 사용(fixed_supports 참조)."
    },
    "load_kn": {
      "default": 10.0,
      "description": "자유 절점에 하향(-Z) 균등 분배할 전체 부과하중.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\".",
      "type": "string"
    },
    "physics": {
      "default": true,
      "description": "false이면 해석 오버레이 없이 같은 부재의 일반 형상을 그려 전후 비교.",
      "type": "boolean"
    },
    "reanalyze": {
      "default": true,
      "description": "false이면 마지막 계산을 재사용하고 표시 옵션(scale, color_by, reveal, physics, title)만 갱신.",
      "type": "boolean"
    },
    "reveal": {
      "default": 1.0,
      "description": "표시할 부재 비율 0..1. 단계별 시공 재생에 사용.",
      "type": "number"
    },
    "scale": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정."
    },
    "self_weight": {
      "default": true,
      "type": "boolean"
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "처짐 한계 평가에 쓸 기준 경간. 생략 시 가장 긴 부재 사용. 6.2 m 장선을 3.1 m씩 분할했다면 6.2 지정."
    },
    "stability": {
      "default": "auto",
      "description": "analysis_02-validate_structure tool과 같은 \"auto\" 또는 \"off\".",
      "type": "string"
    },
    "title": {
      "default": "",
      "type": "string"
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\". \"6.10ab\"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환."
    },
    "view": {
      "default": "deflection",
      "description": "\"deflection\"은 처짐 형상, \"buckling\"은 지배 ULS 조합의 첫 좌굴 모드와 alpha_cr 표시(STABLE ≥ 10, SWAY-SENSITIVE 1~10, UNSTABLE ≤ 1).",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "analysis_method": {
            "type": "string"
          },
          "deflection_limit_mm": {
            "type": "number"
          },
          "elements": {
            "items": {
              "properties": {
                "max_displacement_mm": {
                  "type": "number"
                },
                "source_guids": {
                  "description": "display_guids 또는 객체 관찰에 재사용.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "utilization": {
                  "type": [
                    "number",
                    "null"
                  ]
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "max_displacement_mm": {
            "type": "number"
          },
          "max_utilization": {
            "type": [
              "number",
              "null"
            ]
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "nodes": {
            "type": "integer"
          },
          "passed": {
            "description": "indicative에서 null이면 해석까지 완료했으며 재료 내력의 합격 판정은 생략.",
            "type": [
              "boolean",
              "null"
            ]
          },
          "scale": {
            "description": "변형을 화면에 그릴 때 적용한 과장 배율.",
            "type": "number"
          },
          "span_m": {
            "type": "number"
          },
          "status": {
            "type": "string"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 4. analysis_04-export_structural_report

**CoS · beyond**

```txt
구조 검증 이력의 Markdown 보고서 생성. 각 실행에 실제 엔진과 적용 입력을 기록하고, 저장되지 않은 과거 입력은 알 수 없음으로 표시.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "limit": {
      "default": 50,
      "description": "최대 500회.",
      "type": "integer"
    },
    "path": {
      "default": "",
      "description": "관리형은 선택한 Plan 산출물 폴더 기준 상대 경로(생략 시 reports/structural-validation.md). 독립 실행에서 생략 시 사용자 데이터의 reports/structural-validation-<timestamp>.md.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "limit": {
      "default": 50,
      "description": "최대 500회.",
      "type": "integer"
    },
    "path": {
      "default": "",
      "description": "관리형은 선택한 Plan 산출물 폴더 기준 상대 경로(생략 시 reports/structural-validation.md). 독립 실행에서 생략 시 사용자 데이터의 reports/structural-validation-<timestamp>.md.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "latest_method": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "path": {
            "type": "string"
          },
          "runs": {
            "type": "integer"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 5. analysis_05-check_egress

**CoS · beyond**

```txt
층별 출구 수·유효 폭·이격·보행거리 예비 검토. Rhino에서 형상이나 경로를 읽지 않으므로 실제 층 경계와 문 중심·유효 폭, 가장 불리한 보행 경로를 직접 측정해 입력. 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사.

출구는 문마다 한 번만 입력. 중복 중심, 좌표·폭 누락, 비유한 수, 음수 폭·거리·면적, 양의 정수가 아닌 층수, 면적이 0인 경계는 거절. 폭 0은 폭 부족 판정을 위해 허용.

비업무 용도의 보행거리는 업무용 기준으로 대체. 스프링클러가 있는 막다른 복도도 업무용 기준을 쓰며 용도 경고는 별도로 나오지 않음. 경계값에서는 표시값 반올림으로 판정이 달라 보일 수 있음. BCI와 통상적인 IBC 수치를 사용하므로 source_note·warnings를 프로젝트 적용 법규와 대조.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "dead_end_m": {
      "default": 0.0,
      "description": "가장 긴 막다른 복도 길이. 0이면 검사 생략.",
      "type": "number"
    },
    "exits": {
      "description": "문마다 {\"name\": string, \"x_mm\": number, \"y_mm\": number, \"width_mm\": number}. 좌표는 문 중심, 폭은 유효 피난 폭.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "net_area_m2": {
      "default": 0.0,
      "description": "실제 재실 면적. 0이면 층 경계의 직사각형 면적 사용.",
      "type": "number"
    },
    "occupancy": {
      "default": "business",
      "description": "business, mercantile, assembly_unconcentrated, classroom, residential, storage.",
      "type": "string"
    },
    "plate_bounds_mm": {
      "description": "층 바닥 경계 [min_x, min_y, max_x, max_y].",
      "items": {
        "type": "number"
      },
      "type": "array"
    },
    "sprinklered": {
      "default": true,
      "description": "전체 구역 설치 기준.",
      "type": "boolean"
    },
    "stories": {
      "default": 1,
      "description": "출구가 담당하는 층수. 2층 이상이면 최소 2개 출구와 계단 폭 계수(7.6 mm/인) 적용.",
      "type": "integer"
    },
    "travel_distances_m": {
      "default": [],
      "description": "입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략.",
      "items": {
        "type": "number"
      },
      "type": "array"
    }
  },
  "required": [
    "plate_bounds_mm",
    "exits"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "dead_end_m": {
      "default": 0.0,
      "description": "가장 긴 막다른 복도 길이. 0이면 검사 생략.",
      "type": "number"
    },
    "exits": {
      "description": "문마다 {\"name\": string, \"x_mm\": number, \"y_mm\": number, \"width_mm\": number}. 좌표는 문 중심, 폭은 유효 피난 폭.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "net_area_m2": {
      "default": 0.0,
      "description": "실제 재실 면적. 0이면 층 경계의 직사각형 면적 사용.",
      "type": "number"
    },
    "occupancy": {
      "default": "business",
      "description": "business, mercantile, assembly_unconcentrated, classroom, residential, storage.",
      "type": "string"
    },
    "plate_bounds_mm": {
      "description": "층 바닥 경계 [min_x, min_y, max_x, max_y].",
      "items": {
        "type": "number"
      },
      "type": "array"
    },
    "sprinklered": {
      "default": true,
      "description": "전체 구역 설치 기준.",
      "type": "boolean"
    },
    "stories": {
      "default": 1,
      "description": "출구가 담당하는 층수. 2층 이상이면 최소 2개 출구와 계단 폭 계수(7.6 mm/인) 적용.",
      "type": "integer"
    },
    "travel_distances_m": {
      "default": [],
      "description": "입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략.",
      "items": {
        "type": "number"
      },
      "type": "array"
    }
  },
  "required": [
    "plate_bounds_mm",
    "exits",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "area_m2": {
            "type": "number"
          },
          "checks": {
            "items": {
              "properties": {
                "basis": {
                  "type": "string"
                },
                "check": {
                  "type": "string"
                },
                "passed": {
                  "type": "boolean"
                },
                "provided": {
                  "type": "number"
                },
                "required": {
                  "type": "number"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "gross_area_m2": {
            "description": "입력 경계의 직사각형 면적.",
            "type": "number"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "occupancy": {
            "type": "string"
          },
          "occupant_load": {
            "description": "재실 면적을 용도별 1인당 면적으로 나누어 올림.",
            "type": "integer"
          },
          "passed": {
            "description": "수행한 검사만의 종합 판정. 길이를 입력하지 않은 경로는 미검사.",
            "type": "boolean"
          },
          "source_note": {
            "type": "string"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 6. asset_01-audit_drawing

**CoS · beyond**

```txt
저장된 도면 패키지의 SVG·DXF를 파일 해시 목록과 대조. 빈 해시 목록, 누락·변경 파일, 패키지 외부 경로, 파일시스템 링크는 오류. 원본을 찾으면 원본 변경도 검사.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "package_dir": {
      "description": "도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_glb": {
      "default": "",
      "description": "원본이 바뀌었는지 비교할 GLB. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 라이브러리에서 원본을 찾을 수 있으면 생략 가능.",
      "type": "string"
    }
  },
  "required": [
    "package_dir"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "package_dir": {
      "description": "도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_glb": {
      "default": "",
      "description": "원본이 바뀌었는지 비교할 GLB. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 라이브러리에서 원본을 찾을 수 있으면 생략 가능.",
      "type": "string"
    }
  },
  "required": [
    "package_dir",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "asset_id": {
      "description": "패키지 원본 ID. custom-*는 등록 자산 ID로 사용할 수 없음.",
      "type": "string"
    },
    "checked_files": {
      "description": "파일 해시 검사 건수. 시각 검토는 별도.",
      "type": "integer"
    },
    "error_code": {
      "type": "string"
    },
    "failures": {
      "items": {},
      "type": "array"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "source_geometry": {
      "description": "current, source_file_current, stale, not_checked. not_checked이면 success여도 원본은 미비교.",
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 7. asset_02-generate_drawing_views

**CoS · beyond**

```txt
등록 3DM 또는 사용자 GLB 메시의 평면·정면·우측면 실루엣 생성. 실물 크기 mm DXF와 축척 SVG를 출력. 세 뷰가 A3에 들어가면 시트 SVG도 생성하며, 시트 없이도 성공 가능.

정면은 좌표계 기준. 실루엣에 단면·내부 가시선·은선은 없으며 축척별 단순화로 작은 윤곽이 달라질 수 있음. 결과는 별도 drawing-runs에 저장하고 등록 자산의 도면은 갱신하지 않음.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "default": "",
      "description": "등록 3DM 자산 ID. source_glb와 택일.",
      "type": "string"
    },
    "input_units": {
      "default": "",
      "description": "source_glb를 지정하면 GLB 원본 단위 mm 또는 m 필수.",
      "type": "string"
    },
    "scales": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 정수 축척 분모 1~4개(5~1000). 생략 시 [50, 100]."
    },
    "source_glb": {
      "default": "",
      "description": "정적·비압축 삼각형 GLB(최대 100 MB, 250,000 삼각형).\n관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_references": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "도면에 첨부하는 참고 출처. 원본 모델의 생성 이력 증빙과는 별도.\n필수 키: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.\nrelationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference."
    },
    "up_axis": {
      "default": "y",
      "description": "GLB 위쪽 축 y 또는 z. y는 (X, -Z, Y)로 변환. 등록 3DM에는 적용하지 않음.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "default": "",
      "description": "등록 3DM 자산 ID. source_glb와 택일.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "input_units": {
      "default": "",
      "description": "source_glb를 지정하면 GLB 원본 단위 mm 또는 m 필수.",
      "type": "string"
    },
    "scales": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 정수 축척 분모 1~4개(5~1000). 생략 시 [50, 100]."
    },
    "source_glb": {
      "default": "",
      "description": "정적·비압축 삼각형 GLB(최대 100 MB, 250,000 삼각형).\n관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_references": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "도면에 첨부하는 참고 출처. 원본 모델의 생성 이력 증빙과는 별도.\n필수 키: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.\nrelationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference."
    },
    "up_axis": {
      "default": "y",
      "description": "GLB 위쪽 축 y 또는 z. y는 (X, -Z, Y)로 변환. 등록 3DM에는 적용하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "manifest": {
      "properties": {},
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "package_dir": {
      "description": "asset_01-audit_drawing tool의 package_dir에 그대로 전달. 관리형은 프로젝트 상대 경로이며 다른 드라이브의 라이브러리는 절대 경로 유지.",
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 8. asset_03-get_drawings

**CoS · beyond**

```txt
등록 자산의 저장 도면 패키지 조회. 도면은 배치 인스턴스 변환을 적용하지 않은 자산 원본 형상의 투영. manifest에서 파일·축척·치수·출처·투영 한계를 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "manifest": {
      "properties": {},
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "package_dir": {
      "description": "field_groups에 all을 지정해 반환받은 경로를 asset_01-audit_drawing tool의 package_dir에 전달.",
      "type": "string"
    },
    "plan_svg_uri": {
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 9. asset_04-get

**CoS · beyond**

```txt
모델·2D 자산의 등록 정보와 사용 가능 상태 조회. field_groups에 paths를 지정하면 원본·모델 경로를 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "description": "조회에 사용한 asset_id는 응답에 반복되지 않을 수 있음.",
      "type": "boolean"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "description": "조회에 사용한 asset_id는 응답에 반복되지 않을 수 있음.",
      "type": "boolean"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset": {
            "properties": {
              "drawing_ready": {
                "description": "현재 원본과 일치하는 도면 패키지가 준비된 상태.",
                "type": "boolean"
              },
              "file_available": {
                "description": "원본·등록 파일의 존재 여부.",
                "type": "boolean"
              },
              "model_status": {
                "description": "ready, needs_conversion, needs_refresh 등. source_only인 자산은 배치 전 변환 필요.",
                "type": "string"
              },
              "name": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 10. asset_05-list

**CoS · beyond**

```txt
모델·2D 자산 목록과 배치 준비 상태 조회. 상세 조회용 ID는 include_ids=true로 포함.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "빈 값은 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 20,
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "빈 값은 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 20,
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "description": "추가 준비가 필요한 항목은 next_tool·next_step_guide 참고.",
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "library_id": {
            "description": "include_ids=true일 때 포함.",
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "purpose": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "description": "true이면 같은 필터로 offset에 이번에 반환된 자산 수를 더해 다음 페이지 조회.",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 11. asset_06-place

**CoS · beyond**

```txt
모델·2D 자산을 Rhino 문서에 블록으로 배치. 3DM은 원본에 연결되며 정의를 갱신하면 같은 정의를 사용하는 기존 배치에 반영.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준.",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "균일 배치 축척(0 초과 100 이하).",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준.",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "균일 배치 축척(0 초과 100 이하).",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위).",
      "type": "number"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset_id": {
            "type": "string"
          },
          "definition_created": {
            "description": "공유 정의 갱신 시 definition_refreshed·affected_existing_instances가 추가될 수 있음.",
            "type": "boolean"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_applied": {
            "description": "null이면 변경 적용 여부 미확인.",
            "type": [
              "boolean",
              "null"
            ]
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "object_guid": {
            "description": "삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용.",
            "type": "string"
          },
          "requires_reconciliation": {
            "description": "true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.",
            "type": "boolean"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 12. asset_07-prepare

**CoS · beyond**

```txt
원본 사본을 시각 검토해 등록용 3DM을 준비. inspect로 작업을 만들고, 수정이 필요할 때만 normalize 실행. 첫 verify가 생성한 최종 미리보기를 확인한 뒤 같은 해시·이름·ID로 verify를 다시 호출.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "summary, parts, previews, provenance, all. 생략 시 미리보기 경로 포함, []는 요약. 페이지 처리는 parts에만 적용."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "input_units": {
      "default": "",
      "description": "OBJ/STL/PLY/OFF/GLB/glTF의 측정된 원본 단위(mm, cm, m, in, ft). inspect 이후 생략. 3DM은 내장 단위 유지.",
      "type": "string"
    },
    "job_dir": {
      "default": "",
      "description": "이전 응답의 job_dir. normalize·verify·status에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "limit": {
      "default": 50,
      "description": "부품 목록 페이지당 1~200개.",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    },
    "review": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "normalize: {vision_reviewed:true, inspected_sha256:\"확인한 해시\", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:\"ID\", reason:\"사유\"}]}. 생략한 변환은 그대로 두며 translation은 원본 단위. 최종 미리보기 확인 후 verify: {vision_reviewed:true, final_sha256:\"확인한 해시\", name:\"이름\", asset_id:\"ID\"}."
    },
    "source_file": {
      "default": "",
      "description": "inspect에 사용할 모델. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 원본 바이트는 보존.",
      "type": "string"
    },
    "stage": {
      "description": "inspect, normalize, verify, status. status는 저장 근거만 조회하며 네이티브 실행 재개나 단계 갱신은 하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "stage"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "summary, parts, previews, provenance, all. 생략 시 미리보기 경로 포함, []는 요약. 페이지 처리는 parts에만 적용."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "input_units": {
      "default": "",
      "description": "OBJ/STL/PLY/OFF/GLB/glTF의 측정된 원본 단위(mm, cm, m, in, ft). inspect 이후 생략. 3DM은 내장 단위 유지.",
      "type": "string"
    },
    "job_dir": {
      "default": "",
      "description": "이전 응답의 job_dir. normalize·verify·status에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "limit": {
      "default": 50,
      "description": "부품 목록 페이지당 1~200개.",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    },
    "review": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "normalize: {vision_reviewed:true, inspected_sha256:\"확인한 해시\", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:\"ID\", reason:\"사유\"}]}. 생략한 변환은 그대로 두며 translation은 원본 단위. 최종 미리보기 확인 후 verify: {vision_reviewed:true, final_sha256:\"확인한 해시\", name:\"이름\", asset_id:\"ID\"}."
    },
    "source_file": {
      "default": "",
      "description": "inspect에 사용할 모델. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 원본 바이트는 보존.",
      "type": "string"
    },
    "stage": {
      "description": "inspect, normalize, verify, status. status는 저장 근거만 조회하며 네이티브 실행 재개나 단계 갱신은 하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "stage",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "job_dir": {
      "description": "이후 단계에 전달. asset_09-register tool에는 preparation_job으로 전달.",
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "next_stage": {
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "ready_for_registration": {
      "description": "현재 파일 해시에 대해 호출자가 이미지 검토를 확인한 상태. 형상 적합성은 별도 판단.",
      "type": "boolean"
    },
    "review_evidence": {
      "type": "string"
    },
    "source_3dm": {
      "description": "검토를 마친 최종 3DM. 검토한 name·asset_id와 함께 asset_09-register tool에 전달.",
      "type": "string"
    },
    "state": {
      "description": "ready일 때만 source_3dm 제공. running·unconfirmed·failed이면 status=error.",
      "type": "string"
    },
    "status": {
      "description": "passed는 해당 단계의 검사 통과, pending은 검사 대기, error는 실패 또는 완료 미확정. 등록 가능 여부는 ready_for_registration으로 확인.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 13. asset_08-refresh

**CoS · beyond**

```txt
편집·저장한 등록 3DM을 다시 측정해 평면·입면 도면을 새 리비전으로 발행. 원본 경로와 이전 도면은 보존. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외.

열린 Rhino 문서의 연결 블록 갱신·저장은 별도. 공유 정의를 갱신하면 기존 인스턴스에 반영되며 배치 당시 메타데이터는 유지.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "asset": {
      "properties": {},
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "live_index_refreshed": {
      "description": "게시 완료 후 인덱스 갱신만 실패했다면 재연결.",
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_path": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "package_dir": {
      "type": "string"
    },
    "previous_files_retained": {
      "description": "이전 도면, 매니페스트 백업, 원본 리비전 사본 보존 여부.",
      "type": "boolean"
    },
    "registration_applied": {
      "description": "true이면 인덱스 갱신 오류가 있어도 게시 완료. 다시 게시하기 전에 상태 확인.",
      "type": "boolean"
    },
    "rhino_linked_instances_updated": {
      "type": "boolean"
    },
    "source_path_preserved": {
      "type": "boolean"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 14. asset_09-register

**CoS · beyond**

```txt
검토한 3DM을 모델 라이브러리에 등록하고 치수·평면·입면 실루엣 도면을 생성. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외. 준비를 마쳤어도 파생 메시가 250,000 삼각형을 넘으면 등록 실패. 등록 결과는 asset_04-get tool에서 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 ID와 일치해야 함.",
      "type": "string"
    },
    "category": {
      "default": "other",
      "type": "string"
    },
    "description": {
      "default": "",
      "type": "string"
    },
    "name": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.",
      "type": "string"
    },
    "preparation_job": {
      "default": "",
      "description": "완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "replace_existing": {
      "default": false,
      "description": "true일 때만 같은 ID의 기존 자산 교체.",
      "type": "boolean"
    },
    "source_3dm": {
      "description": "관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.",
      "type": "string"
    },
    "source_url": {
      "default": "",
      "type": "string"
    },
    "tags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "source_3dm",
    "asset_id",
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 ID와 일치해야 함.",
      "type": "string"
    },
    "category": {
      "default": "other",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "description": {
      "default": "",
      "type": "string"
    },
    "name": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.",
      "type": "string"
    },
    "preparation_job": {
      "default": "",
      "description": "완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "replace_existing": {
      "default": false,
      "description": "true일 때만 같은 ID의 기존 자산 교체.",
      "type": "boolean"
    },
    "source_3dm": {
      "description": "관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.",
      "type": "string"
    },
    "source_url": {
      "default": "",
      "type": "string"
    },
    "tags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null
    }
  },
  "required": [
    "source_3dm",
    "asset_id",
    "name",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "asset": {
      "properties": {},
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "library_dir": {
      "type": "string"
    },
    "linked_instances_may_update": {
      "description": "기존 원본을 교체하면 해당 원본에 연결된 인스턴스에 영향 가능.",
      "type": "boolean"
    },
    "live_index_refreshed": {
      "description": "게시 완료 후 인덱스 갱신만 실패했다면 재등록 없이 재연결.",
      "type": "boolean"
    },
    "manifest_path": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "model_path": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "package_dir": {
      "description": "DXF와 치수는 mm 단위.",
      "type": "string"
    },
    "previous_files_retained": {
      "description": "교체 전 원본·도면·매니페스트 백업 보존 여부.",
      "type": "boolean"
    },
    "previous_source_sha256": {
      "type": [
        "string",
        "null"
      ]
    },
    "registration_applied": {
      "description": "게시 결과가 불명확하면 null과 requires_reconciliation 반환. 상태 확인 없이 재시도 금지.",
      "type": [
        "boolean",
        "null"
      ]
    },
    "source_path_preserved": {
      "type": "boolean"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 15. asset_10-search_repository

**CoS · beyond**

```txt
모델·2D 요소 아카이브 검색. 후보가 limit에서 잘리면 검색어나 유형을 좁혀 다시 조회. 원본만 있는 자산은 변환이 필요할 수 있으며 상세 정보·경로는 후보 ID로 asset_04-get tool에서 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "drawing_ready": {
      "default": false,
      "type": "boolean"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "kind": {
      "default": "all",
      "description": "all, element, model.",
      "type": "string"
    },
    "limit": {
      "default": 20,
      "description": "1..100으로 보정.",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "drawing_ready": {
      "default": false,
      "type": "boolean"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "kind": {
      "default": "all",
      "description": "all, element, model.",
      "type": "string"
    },
    "limit": {
      "default": 20,
      "description": "1..100으로 보정.",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "assets": {
      "description": "id를 후속 조회의 asset_id로 전달.",
      "items": {
        "type": "object"
      },
      "type": "array"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "total": {
      "description": "limit 적용 전 전체 일치 건수. 다음 페이지 없음.",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>


### 16. asset_11-search

**CoS · beyond**

```txt
모델·2D 자산을 검색어·분류·최대 치수로 검색. 단어가 하나라도 일치하면 포함하고 일치 단어가 많은 순으로 반환. 치수 필터는 등록 치수를 비교하며 해당 치수가 없는 자산도 포함할 수 있음. include_ids=true로 얻은 ID를 asset_04-get tool에 전달해 상세 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 10,
      "description": "페이지당 1~100개.",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 10,
      "description": "페이지당 1~100개.",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용.",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터).",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "description": "true이면 같은 필터로 offset에 이번 반환 건수를 더해 다음 페이지 조회.",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 17. capture_01-conditioning_pass

**CoS · beyond**

```txt
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG 및 카메라 기록 저장. 촬영 중 뷰가 바뀌며 전체 뷰 상태가 복원되지 않을 수 있음. 패스별 PNG 생성과 대상 가시성은 출력 파일에서 확인. 같은 출력 폴더를 재사용하면 기존 파일을 덮어쓰고 일부 이전 프레임이 남을 수 있음.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "chunk": {
      "default": 16,
      "description": "청크당 프레임 수.",
      "type": "integer"
    },
    "edge_mode": {
      "default": "Technical",
      "description": "에지 패스에 사용할 뷰 메뉴의 래스터 표시 모드 이름 또는 GUID. 기본 Technical. depth는 별도 깊이 버퍼를 사용.",
      "type": "string"
    },
    "fps": {
      "default": 16,
      "type": "integer"
    },
    "height": {
      "default": 480,
      "description": "짝수 픽셀.",
      "type": "integer"
    },
    "invert_depth": {
      "default": false,
      "description": "false이면 가까울수록 밝게 표현.",
      "type": "boolean"
    },
    "out_dir": {
      "default": "",
      "description": "관리형은 먼저 Plan을 선택한 뒤 산출물 폴더 기준 상대 경로 사용(생략 시 conditioning). 독립 실행에서 생략 시 현재 작업 폴더.",
      "type": "string"
    },
    "passes": {
      "default": "rgb,edge,depth",
      "description": "쉼표로 구분한 rgb, edge, depth.",
      "type": "string"
    },
    "rgb_mode": {
      "default": "Rendered",
      "description": "RGB 패스에 사용할 뷰 메뉴의 래스터 표시 모드 이름 또는 GUID. 기본 Rendered. 이름이 중복되면 GUID 사용.",
      "type": "string"
    },
    "shot": {
      "description": "카메라 경로를 담은 JSON 문자열. orbit은 center:[x,y,z], radius, height, 선택 start_deg·end_deg·lens·target_height. track은 cam0·cam1·target0·target1 좌표, 선택 lens. keyframes는 camera·target·선택 lens를 가진 keyframes 배열. type으로 경로 유형 지정. frames 생략 시 81, lens는 mm, 좌표는 문서 단위.",
      "type": "string"
    },
    "width": {
      "default": 832,
      "description": "짝수 픽셀.",
      "type": "integer"
    }
  },
  "required": [
    "shot"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "chunk": {
      "default": 16,
      "description": "청크당 프레임 수.",
      "type": "integer"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "fps": {
      "default": 16,
      "type": "integer"
    },
    "height": {
      "default": 480,
      "description": "짝수 픽셀.",
      "type": "integer"
    },
    "invert_depth": {
      "default": false,
      "description": "false이면 가까울수록 밝게 표현.",
      "type": "boolean"
    },
    "out_dir": {
      "default": "",
      "description": "관리형은 먼저 Plan을 선택한 뒤 산출물 폴더 기준 상대 경로 사용(생략 시 conditioning). 독립 실행에서 생략 시 현재 작업 폴더.",
      "type": "string"
    },
    "passes": {
      "default": "rgb,edge,depth",
      "description": "쉼표로 구분한 rgb, edge, depth.",
      "type": "string"
    },
    "shot": {
      "description": "카메라 경로를 담은 JSON 문자열. orbit은 center:[x,y,z], radius, height, 선택 start_deg·end_deg·lens·target_height. track은 cam0·cam1·target0·target1 좌표, 선택 lens. keyframes는 camera·target·선택 lens를 가진 keyframes 배열. type으로 경로 유형 지정. frames 생략 시 81, lens는 mm, 좌표는 문서 단위.",
      "type": "string"
    },
    "width": {
      "default": 832,
      "description": "짝수 픽셀.",
      "type": "integer"
    }
  },
  "required": [
    "shot",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "camera_json": {
            "description": "계획 경로 전체 기록. 촬영이 일부만 끝나도 frames[].camera·target·lens_mm는 전체 경로 기준.",
            "type": "string"
          },
          "document": {
            "properties": {},
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "errors": {
            "description": "실패 청크의 프레임 범위와 메시지. 일부 출력 파일이 남을 수 있음.",
            "items": {},
            "type": "array"
          },
          "fps": {
            "type": "number"
          },
          "frames_captured": {
            "description": "실행 완료 응답을 받은 청크에 포함된 프레임 수.",
            "type": "integer"
          },
          "frames_requested": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "out_dir": {
            "description": "패스별 PNG와 doc.json, camera.json, zrange.csv, summary.json 저장 위치.",
            "type": "string"
          },
          "passes": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "resolution": {
            "description": "[너비, 높이].",
            "items": {
              "type": "number"
            },
            "type": "array"
          },
          "status": {
            "description": "executed는 모든 청크 실행 완료. error는 완료가 확인된 청크 없이 실패, partial은 앞선 청크의 완료 후 실패.",
            "type": "string"
          },
          "videos": {
            "properties": {
              "rgb": {
                "type": [
                  "string",
                  "null"
                ]
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 18. capture_02-inspection

**CoS · beyond**

```txt
작업 화면을 유지하면서 여러 시점과 객체 범위를 한 PNG로 비교. 범위는 문서 표시 상태 기준이며 픽셀 가시성이나 가림은 판정하지 않는다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않는다.

뷰 메뉴의 표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. Wireframe은 곡선·와이어, Shaded는 면과 입체, Technical은 가려진 선을 포함한 선 표현 검토에 적합하다. 메뉴에 등록된 사용자 정의 래스터 모드도 선택할 수 있으며 이름이 중복되면 GUID를 사용한다.

최상위 모델 객체 GUID는 inspect_02-get_objects tool의 include_ids=true로 조회. 공통 object_ids를 지정한 뒤 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]로 같은 대상을 평면과 사시에서 비교한다. 원본 뷰 방향에서 대상에 맞춰 확대하려면 공통 또는 타일별 object_ids와 views=[{"direction":"current","frame_objects":true}]를 사용한다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 유지한다.

공통 또는 타일별 object_ids에 최상위 블록 인스턴스를 지정하면 전체 호출이 실패하고 메시지에 입력 위치와 블록 GUID가 표시된다. 다른 이유로 일부 타일만 실패하면 complete=false이며 tiles에서 실패 이유를 확인할 수 있다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "columns": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1..뷰 개수. 생략 시 자동 격자."
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "default": 480,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용.",
      "type": "integer"
    },
    "model_view_id": {
      "default": "",
      "description": "활성화하지 않고 사용할 모델 뷰포트 GUID. Layout·Detail에서 작업 중일 때도 지정 가능.",
      "type": "string"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "모든 타일에 적용할 최상위 객체 GUID 1..4096개. 블록 인스턴스 제외. 타일별 object_ids와 함께 지정할 수 없다."
    },
    "views": {
      "description": "타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw. display_mode: 뷰 메뉴의 래스터 모드 이름 또는 GUID. RhinoBeyond에서는 세션의 공개 입력에 열거된 GUID를 사용한다. label: 최대 120자. object_ids: 블록 인스턴스를 제외한 최상위 객체 GUID 1..512개. 생략하거나 비우면 공통 범위 또는 문서 표시 상태를 사용한다.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "width": {
      "default": 640,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용.",
      "type": "integer"
    }
  },
  "required": [
    "views"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "columns": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1..뷰 개수. 생략 시 자동 격자."
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "default": 480,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용.",
      "type": "integer"
    },
    "model_view_id": {
      "default": "",
      "description": "활성화하지 않고 사용할 모델 뷰포트 GUID. Layout·Detail에서 작업 중일 때도 지정 가능.",
      "type": "string"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "모든 타일에 적용할 최상위 객체 GUID 1..4096개. 블록 인스턴스 제외. 타일별 object_ids와 함께 지정할 수 없다."
    },
    "views": {
      "description": "타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw. display_mode: 뷰 메뉴의 래스터 모드 이름 또는 GUID. RhinoBeyond에서는 세션의 공개 입력에 열거된 GUID를 사용한다. label: 최대 120자. object_ids: 블록 인스턴스를 제외한 최상위 객체 GUID 1..512개. 생략하거나 비우면 공통 범위 또는 문서 표시 상태를 사용한다.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "direction": {
            "type": "string"
          },
          "frame_objects": {
            "type": "boolean"
          },
          "label": {
            "type": "string"
          },
          "object_ids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "width": {
      "default": 640,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용.",
      "type": "integer"
    }
  },
  "required": [
    "views",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "complete": {
      "type": "boolean"
    },
    "error_code": {
      "type": "string"
    },
    "image_file": {
      "description": "저장에 실패해도 PNG는 전달될 수 있다.",
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "lifetime": {
          "description": "plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.",
          "type": "string"
        },
        "path": {
          "description": "프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.",
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "description": "saved일 때만 path 사용 가능.",
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "tiles": {
      "description": "실패한 타일도 포함.",
      "items": {
        "properties": {
          "direction": {
            "type": "string"
          },
          "display_mode": {
            "description": "성공한 타일에 실제로 적용된 모드.",
            "properties": {
              "id": {
                "type": "string"
              },
              "name": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "index": {
            "description": "0부터 시작.",
            "type": "integer"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

</details>


### 19. capture_03-current_view

**CoS · beyond**

```txt
현재 Rhino 모델 뷰포트를 화면 색과 선 표현으로 PNG 캡처. 문서의 PrintDisplay 설정은 유지한다. 대상 지정은 실제 선택과 카메라를 바꾸고 isolate와 display_mode도 작업 화면에 적용된다. 확대 검수는 이미지를 확대하는 대신 실제 Rhino 뷰포트를 확대한 뒤 대상을 지정하지 않고 캡처한다.

표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. 작업 화면을 유지하면서 여러 방향이나 모드를 비교하려면 capture_02-inspection tool을 사용한다. 격리는 Rhino Unisolate로 해제할 수 있다. 잠긴 주변 객체는 격리 중에도 보일 수 있으며 선택과 카메라 상태는 별도로 확인한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "default": 1,
      "description": "레이블 확장 깊이 1..8.",
      "type": "integer"
    },
    "display_mode": {
      "default": "",
      "description": "뷰 메뉴에 등록된 래스터 모드 이름 또는 GUID.",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용."
    },
    "include_usage": {
      "default": false,
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "isolate": {
      "default": false,
      "description": "target_ids가 필요하며 확대 전에 격리.",
      "type": "boolean"
    },
    "labels": {
      "default": false,
      "description": "주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100.",
      "type": "integer"
    },
    "target_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처."
    },
    "target_kind": {
      "default": "object",
      "description": "object, group, block, holon. block에는 배치 객체 ID 사용. object 이외에는 target_ids 필요.",
      "type": "string"
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "default": 1,
      "description": "레이블 확장 깊이 1..8.",
      "type": "integer"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용."
    },
    "include_usage": {
      "default": false,
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "isolate": {
      "default": false,
      "description": "target_ids가 필요하며 확대 전에 격리.",
      "type": "boolean"
    },
    "labels": {
      "default": false,
      "description": "주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100.",
      "type": "integer"
    },
    "target_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처."
    },
    "target_kind": {
      "default": "object",
      "description": "object, group, block, holon. block에는 배치 객체 ID 사용. object 이외에는 target_ids 필요.",
      "type": "string"
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "failed_stage": {
      "description": "validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.",
      "type": "string"
    },
    "focus_observation": {
      "properties": {
        "after_failure": {
          "properties": {
            "camera_location": {
              "description": "문서 단위의 [x, y, z].",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "camera_target": {
              "description": "문서 단위의 [x, y, z].",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "frustum": {
              "description": "[left, right, bottom, top, near, far] 순서.",
              "items": {
                "type": "number"
              },
              "maxItems": 6,
              "minItems": 6,
              "type": "array"
            },
            "observation_error": {
              "type": "string"
            },
            "parallel_projection": {
              "type": "boolean"
            },
            "viewport_id": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "before_zoom": {
          "properties": {
            "camera_location": {
              "description": "문서 단위의 [x, y, z].",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "camera_target": {
              "description": "문서 단위의 [x, y, z].",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "frustum": {
              "description": "[left, right, bottom, top, near, far] 순서.",
              "items": {
                "type": "number"
              },
              "maxItems": 6,
              "minItems": 6,
              "type": "array"
            },
            "observation_error": {
              "type": "string"
            },
            "parallel_projection": {
              "type": "boolean"
            },
            "viewport_id": {
              "type": "string"
            }
          },
          "type": "object"
        },
        "target_bounds": {
          "description": "문서 단위의 대상 합집합 경계.",
          "properties": {
            "max": {
              "description": "[x, y, z] 순서.",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "min": {
              "description": "[x, y, z] 순서.",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            }
          },
          "type": "object"
        },
        "target_bounds_error": {
          "type": "string"
        },
        "target_count": {
          "type": "integer"
        },
        "zoom_bounding_box": {
          "type": [
            "boolean",
            "null"
          ]
        },
        "zoom_extents_selected": {
          "type": [
            "boolean",
            "null"
          ]
        }
      },
      "type": "object"
    },
    "image_file": {
      "description": "저장과 PNG 전달은 별개로 확인.",
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "lifetime": {
          "description": "plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.",
          "type": "string"
        },
        "path": {
          "description": "프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.",
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "description": "saved일 때만 path 사용 가능.",
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "mutation_applied": {
      "description": "null이면 뷰 변경 적용을 확인하지 못한 상태.",
      "type": [
        "boolean",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "requires_reconciliation": {
      "description": "true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.",
      "type": "boolean"
    },
    "status": {
      "type": "string"
    },
    "view_change": {
      "properties": {
        "display_mode_changed": {
          "type": [
            "boolean",
            "null"
          ]
        },
        "isolated": {
          "type": [
            "boolean",
            "null"
          ]
        },
        "restore_visibility_command": {
          "description": "격리 가시성만 복구. 카메라와 선택은 별도로 확인.",
          "type": "string"
        },
        "selection_changed": {
          "type": [
            "boolean",
            "null"
          ]
        },
        "zoom_method": {
          "description": "selected는 기본 선택 확대, bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.",
          "enum": [
            "selected",
            "bounding_box"
          ],
          "type": "string"
        },
        "zoom_selected": {
          "description": "선택 확대 또는 대체 경계 확대를 완료하면 true.",
          "type": [
            "boolean",
            "null"
          ]
        }
      },
      "type": "object"
    }
  },
  "type": "object"
}
```

</details>


### 20. capture_04-defined_view

**CoS · beyond**

```txt
저장된 Named View 또는 Layout 용지를 PNG로 캡처. 대상 이름·ID는 inspect_03-get_document_context tool에서 조회한다.

Named View는 저장된 카메라를 사용하며 표시 모드 선택은 capture_02-inspection tool 참고. Layout은 용지·Detail의 기존 모드와 인쇄 색·선폭으로 출력하고 PrintDisplay는 유지한다. Layout에는 픽셀 크기·display_mode를 지정할 수 없고 Detail 레이블도 지원하지 않는다. 인쇄 대상이 없으면 빈 PNG도 정상이다.

PNG 전달과 파일 저장은 별개다. 사용량 추정·경고는 별도 text content로 전달한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "default": 1,
      "description": "레이블 깊이 1..8.",
      "type": "integer"
    },
    "display_mode": {
      "default": "",
      "description": "Named View 전용. 생략 시 Shaded. 뷰 메뉴에 등록된 래스터 모드 이름 또는 GUID.",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Named View 전용. 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용."
    },
    "include_usage": {
      "default": false,
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "labels": {
      "default": false,
      "description": "최대 200개. 주변 레이블과 겹칠 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다.",
      "type": "integer"
    },
    "target": {
      "description": "기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.",
      "type": "string"
    },
    "target_kind": {
      "description": "named_view 또는 layout.",
      "type": "string"
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Named View 전용. 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용."
    }
  },
  "required": [
    "target_kind",
    "target"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "default": 1,
      "description": "레이블 깊이 1..8.",
      "type": "integer"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Named View 전용. 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용."
    },
    "include_usage": {
      "default": false,
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "labels": {
      "default": false,
      "description": "최대 200개. 주변 레이블과 겹칠 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다.",
      "type": "integer"
    },
    "target": {
      "description": "기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.",
      "type": "string"
    },
    "target_kind": {
      "description": "named_view 또는 layout.",
      "type": "string"
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Named View 전용. 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용."
    }
  },
  "required": [
    "target_kind",
    "target",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "image_file": {
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "lifetime": {
          "description": "plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.",
          "type": "string"
        },
        "path": {
          "description": "프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.",
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "description": "saved일 때만 path 사용 가능.",
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 21. connect_01-list_up

**CoS**

```txt
열린 Rhino 문서와 이 클라이언트의 연결·시작 요청 조회. 연결된 문서도 targets에 표시된다. 연결하려면 같은 대상의 host_id와 저장된 model_path를 connect_02-session tool에 전달한다. 이후 일반 호출은 selected_connection_id의 연결을 사용한다.
```

**beyond**

```txt
열린 Rhino 문서와 이 클라이언트의 연결·시작 요청 조회. 연결하려면 같은 대상의 host_id와 저장된 model_path를 connect_02-session tool에 전달한다.
```

<details><summary>CoS · beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {},
  "required": [],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "connections": {
      "items": {
        "properties": {
          "artifact_dir": {
            "description": "연결 단위 임시 작업 폴더.",
            "type": [
              "string",
              "null"
            ]
          },
          "connection_id": {
            "type": [
              "string",
              "null"
            ]
          },
          "host_id": {
            "type": [
              "string",
              "null"
            ]
          },
          "in_flight": {
            "type": "boolean"
          },
          "model_filename": {
            "type": [
              "string",
              "null"
            ]
          },
          "model_path": {
            "type": [
              "string",
              "null"
            ]
          },
          "pid": {
            "type": [
              "integer",
              "null"
            ]
          },
          "reason": {
            "type": "string"
          },
          "slot": {
            "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
            "type": [
              "string",
              "null"
            ]
          },
          "state": {
            "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "error_code": {
      "type": "string"
    },
    "instructions": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "selected_connection_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "starts": {
      "items": {
        "properties": {
          "connection_id": {
            "type": [
              "string",
              "null"
            ]
          },
          "model_path": {
            "description": "시작 요청 모델의 절대 경로.",
            "type": "string"
          },
          "reason": {
            "type": "string"
          },
          "request_id": {
            "description": "같은 시작 요청을 조회할 때 재사용.",
            "type": "string"
          },
          "state": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "targets": {
      "items": {
        "properties": {
          "artifact_dir": {
            "description": "연결 단위 임시 작업 폴더.",
            "type": [
              "string",
              "null"
            ]
          },
          "connection_id": {
            "type": [
              "string",
              "null"
            ]
          },
          "host_id": {
            "type": [
              "string",
              "null"
            ]
          },
          "in_flight": {
            "type": "boolean"
          },
          "model_filename": {
            "type": [
              "string",
              "null"
            ]
          },
          "model_path": {
            "type": [
              "string",
              "null"
            ]
          },
          "pid": {
            "type": [
              "integer",
              "null"
            ]
          },
          "reason": {
            "type": "string"
          },
          "slot": {
            "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
            "type": [
              "string",
              "null"
            ]
          },
          "state": {
            "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

</details>


### 22. connect_02-session

**CoS**

```txt
열린 Rhino 문서에 연결하거나 작업 대상 전환. connect_01-list_up tool의 targets에서 같은 대상의 host_id와 model_path를 가져온다. 유지 중인 연결도 다시 선택할 수 있으며, 선택 후 일반 호출은 그 연결을 사용한다.
```

**beyond**

```txt
열린 Rhino 문서에 연결하고 해당 문서의 연결 ID를 반환.
```

<details><summary>CoS · beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "host_id": {
      "type": "string"
    },
    "model_path": {
      "type": "string"
    }
  },
  "required": [
    "host_id",
    "model_path"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "description": "연결 단위 임시 작업 폴더.",
      "type": [
        "string",
        "null"
      ]
    },
    "connection_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "host_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "in_flight": {
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_filename": {
      "type": [
        "string",
        "null"
      ]
    },
    "model_path": {
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "type": [
        "integer",
        "null"
      ]
    },
    "reason": {
      "type": "string"
    },
    "slot": {
      "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "state": {
      "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "description": "연결 단위 임시 작업 폴더.",
      "type": [
        "string",
        "null"
      ]
    },
    "connection_id": {
      "description": "model_path와 connection_id를 현재 대화의 변수에 함께 저장하고, 이 문서의 후속 호출마다 connection_id를 전달한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "host_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "in_flight": {
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_filename": {
      "type": [
        "string",
        "null"
      ]
    },
    "model_path": {
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "type": [
        "integer",
        "null"
      ]
    },
    "reason": {
      "type": "string"
    },
    "slot": {
      "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "state": {
      "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 23. connect_03-start_session

**CoS**

```txt
저장된 모델을 새 Rhino 창에서 열고 연결. model_path와 시작 시도를 식별하는 request_id 필요.
```

**beyond**

```txt
저장된 모델을 새 Rhino 창에서 열고 해당 문서의 연결 ID를 반환.
```

<details><summary>CoS · beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "model_path": {
      "description": "저장된 로컬 .3dm 파일의 절대 경로.",
      "type": "string"
    },
    "request_id": {
      "description": "시작 시도마다 고유한 값. 지연되거나 결과가 불확실하면 같은 값으로 다시 조회.",
      "maxLength": 128,
      "minLength": 1,
      "type": "string"
    }
  },
  "required": [
    "model_path",
    "request_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "description": "연결 단위 임시 작업 폴더.",
      "type": [
        "string",
        "null"
      ]
    },
    "connection_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "host_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "in_flight": {
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_filename": {
      "type": [
        "string",
        "null"
      ]
    },
    "model_path": {
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "type": [
        "integer",
        "null"
      ]
    },
    "reason": {
      "type": "string"
    },
    "request_id": {
      "description": "대기·실패 상태는 connect_01-list_up tool의 starts에서 확인.",
      "type": "string"
    },
    "slot": {
      "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "state": {
      "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "description": "연결 단위 임시 작업 폴더.",
      "type": [
        "string",
        "null"
      ]
    },
    "connection_id": {
      "description": "model_path와 connection_id를 현재 대화의 변수에 함께 저장하고, 이 문서의 후속 호출마다 connection_id를 전달한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "host_id": {
      "type": [
        "string",
        "null"
      ]
    },
    "in_flight": {
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_filename": {
      "type": [
        "string",
        "null"
      ]
    },
    "model_path": {
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "type": [
        "integer",
        "null"
      ]
    },
    "reason": {
      "type": "string"
    },
    "request_id": {
      "description": "대기·실패 상태는 connect_01-list_up tool의 starts에서 확인.",
      "type": "string"
    },
    "slot": {
      "description": "독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.",
      "type": [
        "string",
        "null"
      ]
    },
    "state": {
      "description": "ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 24. connect_04-disconnect

**CoS**

```txt
선택한 연결 해제. Rhino 창과 문서는 계속 열린 상태로 유지.
```

**beyond**

```txt
지정한 연결 해제. Rhino 창과 문서는 계속 열린 상태로 유지.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {},
  "required": [],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "connection_id": {
      "type": "string"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "model_path": {
      "description": "저장·종료 전에 현재 문서 경로와 대조.",
      "type": [
        "string",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "description": "종료할 Rhino 창은 이 PID와 model_path를 함께 대조해 식별.",
      "type": [
        "integer",
        "null"
      ]
    },
    "reason": {
      "description": "잠금이 남은 경우 그 사유 포함.",
      "type": "string"
    },
    "released": {
      "description": "Rhino가 연결 해제를 확인한 경우 true.",
      "type": "boolean"
    },
    "rhino_closed": {
      "type": "boolean"
    },
    "worker_closed": {
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>


### 25. connect_05-close_session

**CoS**

```txt
선택한 Rhino 문서의 저장 완료를 확인한 뒤 Rhino를 정상 종료.
```

**beyond**

```txt
지정한 연결의 Rhino 문서 저장을 확인한 뒤 Rhino를 정상 종료. 결과 재조회에는 원래의 두 ID를 사용한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request_id": {
      "description": "종료 시도마다 고유한 값. 지연되거나 결과가 불확실하면 같은 값으로 재호출해 기존 결과를 조회.",
      "maxLength": 128,
      "minLength": 1,
      "type": "string"
    }
  },
  "required": [
    "request_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request_id": {
      "description": "종료 시도마다 고유한 값. 지연되거나 결과가 불확실하면 같은 값으로 재호출해 기존 결과를 조회.",
      "maxLength": 128,
      "minLength": 1,
      "type": "string"
    }
  },
  "required": [
    "request_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "connection_id": {
      "type": "string"
    },
    "model_path": {
      "description": "저장·종료 대상의 절대 경로.",
      "type": "string"
    },
    "modified_after": {
      "type": "boolean"
    },
    "modified_before": {
      "type": "boolean"
    },
    "next_step_guide": {
      "type": "string"
    },
    "pid": {
      "description": "프로세스 시작 정보까지 대조한 Rhino PID.",
      "type": "integer"
    },
    "reason": {
      "type": "string"
    },
    "released": {
      "type": "boolean"
    },
    "request_id": {
      "type": "string"
    },
    "rhino_closed": {
      "type": "boolean"
    },
    "save_request_id": {
      "description": "script_03-get_execution tool에서 저장 결과를 조회할 때 사용.",
      "type": "string"
    },
    "saved": {
      "description": "Save 완료와 같은 문서의 modified=false를 모두 확인.",
      "type": "boolean"
    },
    "stage": {
      "type": "string"
    },
    "status": {
      "description": "completed는 저장, Rhino·worker 종료, 연결 소유권 해제를 모두 확인한 상태.",
      "enum": [
        "closing",
        "completed",
        "rejected",
        "save_failed",
        "unconfirmed"
      ],
      "type": "string"
    },
    "worker_closed": {
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>


### 26. context_01-get_policy

**CoS · beyond**

```txt
Almond 도구와 기술 참고 자료 조회. policy를 생략하면 공개 도구 목록과 참고 자료 종류를 반환.

metadata는 User Text 등 객체 메타데이터 키 사전, rhino_scripting은 내장 스크립팅 자료, rhinocode는 코드·명령 실행 지침.

같은 guide_version에서 이미 읽은 지침은 재사용할 수 있다.
```

<details><summary>CoS · beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "policy": {
      "default": "",
      "description": "생략하거나 비워 두면 basic(공개 도구 목록). 참고 자료 종류는 available_policies 참고.",
      "enum": [
        "",
        "basic",
        "metadata",
        "rhino_scripting",
        "rhinocode"
      ],
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "available_policies": {
      "additionalProperties": {
        "type": "string"
      },
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "guide_version": {
      "description": "같은 지침인지 비교할 수 있는 버전 해시.",
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "policy": {
      "additionalProperties": true,
      "type": "object"
    },
    "scripting_skill": {
      "properties": {
        "name": {
          "type": "string"
        },
        "sources": {
          "items": {
            "properties": {
              "path": {
                "description": "저장소 상대 경로. src/mcp/로 시작.",
                "type": "string"
              },
              "sha256": {
                "description": "줄바꿈 등을 정규화한 출처의 해시.",
                "type": "string"
              },
              "text": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "selected_policy": {
      "type": "string"
    },
    "source_refs": {
      "items": {
        "properties": {
          "path": {
            "type": "string"
          },
          "sha256": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "status": {
      "type": "string"
    },
    "text": {
      "type": "string"
    },
    "tools": {
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

</details>


### 27. context_04-get_project_info

**CoS · beyond**

```txt
연결된 Rhino 문서와 프로젝트 작업 정보 조회.

sections에서 필요한 항목을 선택한다. locations·runtime만 요청하면 Rhino 문서를 직접 관찰하지 않는다. named_views와 layouts는 각각 최대 128개이며 include_ids와 관계없이 ID를 포함한다.

project.worksession_files는 활성 문서를 제외한 현재 Worksession 첨부 파일이다. 이 목록과 DB 등록 목록인 project.files는 별개다. Worksession 첨부·해제로 DB 등록은 바뀌지 않는다. 파일 등록과 설명 갱신은 context_05-upsert_project_file tool을 사용한다. Phase와 Scene에는 등록 파일명을 지정한다.

후속 호출에 쓸 Plan·Step ID가 필요하면 include_ids=true. 프로젝트 내부 경로는 project_root를 기준으로 읽는다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "files_limit": {
      "default": 50,
      "description": "등록 파일 페이지 크기. 정수 1..500.",
      "type": "integer"
    },
    "files_offset": {
      "default": 0,
      "description": "등록 파일 페이지의 시작 위치. 0 이상의 정수.",
      "type": "integer"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "project, document, named_views, layouts, layer_tree, locations, runtime. 생략 시 runtime을 제외한 전체."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "files_limit": {
      "default": 50,
      "description": "등록 파일 페이지 크기. 정수 1..500.",
      "type": "integer"
    },
    "files_offset": {
      "default": 0,
      "description": "등록 파일 페이지의 시작 위치. 0 이상의 정수.",
      "type": "integer"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "project, document, named_views, layouts, layer_tree, locations, runtime. 생략 시 runtime을 제외한 전체."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "document": {
      "properties": {
        "absolute_tolerance": {
          "description": "현재 문서 단위.",
          "type": [
            "number",
            "null"
          ]
        },
        "angle_tolerance_radians": {
          "type": [
            "number",
            "null"
          ]
        },
        "layer_count": {
          "description": "활성 레이어만 집계.",
          "type": [
            "integer",
            "null"
          ]
        },
        "modified": {
          "type": [
            "boolean",
            "null"
          ]
        },
        "object_count": {
          "type": [
            "integer",
            "null"
          ]
        },
        "runtime_serial_number": {
          "description": "include_ids=true일 때 포함.",
          "type": [
            "integer",
            "null"
          ]
        },
        "units": {
          "type": [
            "string",
            "null"
          ]
        }
      },
      "type": [
        "object",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "layer_tree": {
      "type": [
        "string",
        "null"
      ]
    },
    "layouts": {
      "items": {
        "properties": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": [
        "array",
        "null"
      ]
    },
    "locations": {
      "properties": {
        "artifact_dir": {
          "description": "선택된 Plan·Loop의 산출물 폴더.",
          "type": [
            "string",
            "null"
          ]
        },
        "artifact_rule": {
          "type": "string"
        },
        "database": {
          "description": "연결된 모델이 공유하는 DB 경로.",
          "type": "string"
        },
        "loop_no": {
          "description": "0은 첫 실행 전 기록.",
          "type": "integer"
        },
        "path_rule": {
          "type": "string"
        },
        "plan_artifact_dir": {
          "description": "프로젝트 기준 상대 경로.",
          "type": [
            "string",
            "null"
          ]
        },
        "plan_id": {
          "type": "string"
        },
        "read_only": {
          "description": "선택한 회차가 최신 회차보다 이전이면 true.",
          "type": "boolean"
        },
        "step_id": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "named_views": {
      "items": {
        "properties": {
          "id": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": [
        "array",
        "null"
      ]
    },
    "next_step_guide": {
      "type": "string"
    },
    "project": {
      "properties": {
        "file_name": {
          "type": [
            "string",
            "null"
          ]
        },
        "file_path": {
          "type": [
            "string",
            "null"
          ]
        },
        "files": {
          "items": {
            "properties": {
              "description": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "file_name": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        },
        "files_page": {
          "properties": {
            "limit": {
              "type": "integer"
            },
            "offset": {
              "type": "integer"
            },
            "total": {
              "type": "integer"
            },
            "truncated": {
              "description": "true면 같은 조건에서 files_offset=offset+limit으로 다음 페이지 조회.",
              "type": "boolean"
            }
          },
          "type": "object"
        },
        "is_bound_document": {
          "description": "현재 Rhino 문서가 이 연결에서 선택한 모델과 일치하는지 확인.",
          "type": "boolean"
        },
        "project_root": {
          "description": "프로젝트 파일 도구에서 상대 경로를 해석하는 기준 디렉터리의 절대 경로.",
          "type": "string"
        },
        "worksession_files": {
          "items": {
            "properties": {
              "file_name": {
                "type": "string"
              },
              "file_path": {
                "description": "다른 드라이브의 파일은 절대 경로.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": [
            "array",
            "null"
          ]
        }
      },
      "type": "object"
    },
    "runtime": {
      "properties": {
        "attachment": {
          "type": "string"
        },
        "port": {
          "type": "integer"
        },
        "python_executable": {
          "description": "현재 worker의 Python 실행 파일 경로.",
          "type": "string"
        },
        "rhino_temp_at_attach": {
          "description": "연결 시 기록한 Rhino 프로세스의 TEMP 경로.",
          "type": [
            "string",
            "null"
          ]
        },
        "rhino_temp_note": {
          "type": "string"
        },
        "rhinocode": {
          "properties": {
            "available": {
              "description": "현재 연결에서 허용된 실행 언어를 사용할 수 있으면 true.",
              "type": "boolean"
            },
            "executable": {
              "type": "string"
            },
            "languages": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "message": {
              "type": "string"
            },
            "pipe_id": {
              "description": "include_ids=true일 때 포함.",
              "type": "string"
            },
            "version": {
              "description": "RhinoCode 인스턴스의 원본 processVersion."
            }
          },
          "type": "object"
        },
        "scratch_root": {
          "type": "string"
        },
        "session_dir": {
          "type": "string"
        },
        "slot": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "status": {
      "type": "string"
    },
    "warnings": {
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

</details>


### 28. context_05-upsert_project_file

**CoS · beyond**

```txt
프로젝트 파일 카탈로그에 모델 파일을 등록하거나 설명을 갱신. 파일명 비교는 Windows 기준이며 수정 시 기존 표기를 유지한다. Rhino 문서 열기나 Worksession 첨부는 별도 작업이다.

등록 목록은 context_04-get_project_info tool의 project.files에서 조회한다. Phase와 Scene에는 목록에 있는 파일명을 사용한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략하거나 null이면 기존 설명 유지. 빈 문자열로 삭제."
    },
    "file_name": {
      "description": "폴더를 뺀 모델 파일명. 프로젝트 안에서 고유해야 한다.",
      "type": "string"
    }
  },
  "required": [
    "file_name"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략하거나 null이면 기존 설명 유지. 빈 문자열로 삭제."
    },
    "file_name": {
      "description": "폴더를 뺀 모델 파일명. 프로젝트 안에서 고유해야 한다.",
      "type": "string"
    }
  },
  "required": [
    "file_name",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "description": {
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "file_name": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 29. diagram_01-get

**CoS · beyond**

```txt
다이어그램 자산의 등록 정보와 원본 파일 상태 조회. 파일이 없는 항목도 조회 가능.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "diagram_02-list tool 또는 diagram_04-search tool에서 얻은 ID. 대소문자와 공백까지 그대로 사용.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. all은 다른 그룹 밖의 등록 필드도 포함."
    },
    "include_ids": {
      "default": false,
      "description": "true면 추가 식별자 포함. 입력 asset_id는 응답에 반복하지 않는다.",
      "type": "boolean"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "diagram_02-list tool 또는 diagram_04-search tool에서 얻은 ID. 대소문자와 공백까지 그대로 사용.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. all은 다른 그룹 밖의 등록 필드도 포함."
    },
    "include_ids": {
      "default": false,
      "description": "true면 추가 식별자 포함. 입력 asset_id는 응답에 반복하지 않는다.",
      "type": "boolean"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset": {
            "properties": {
              "file_available": {
                "type": "boolean"
              },
              "name": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 30. diagram_02-list

**CoS · beyond**

```txt
사람·나무·기호 등 등록된 2D 벡터·CAD 다이어그램 조회. 파일이 없는 항목도 포함한다. 상세 정보는 diagram_01-get tool, 키워드·치수 검색은 diagram_04-search tool.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류값 전체 일치. 대소문자 무시. 비워 두면 전체 조회.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 20,
      "description": "1..50으로 보정.",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "음수는 0으로 보정.",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류값 전체 일치. 대소문자 무시. 비워 두면 전체 조회.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 20,
      "description": "1..50으로 보정.",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "음수는 0으로 보정.",
      "type": "integer"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "library_id": {
            "description": "include_ids=true일 때 포함.",
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_offset": {
            "type": [
              "integer",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "purpose": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 31. diagram_03-place

**CoS · beyond**

```txt
SVG·DWG·DXF 다이어그램을 Rhino 문서에 블록 인스턴스로 배치. requires_reconciliation=true면 문서에서 실제 배치를 확인한 뒤 다음 작업을 결정한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준.",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "양수인 균일 축척. 1은 문서 단위로 변환한 자산의 원래 크기.",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준.",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "양수인 균일 축척. 1은 문서 단위로 변환한 자산의 원래 크기.",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "현재 Rhino 문서 단위.",
      "type": "number"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset_id": {
            "type": "string"
          },
          "definition_created": {
            "type": "boolean"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_applied": {
            "description": "null이면 변경 적용 여부 미확인.",
            "type": [
              "boolean",
              "null"
            ]
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "object_guid": {
            "description": "삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용.",
            "type": "string"
          },
          "requires_reconciliation": {
            "description": "true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.",
            "type": "boolean"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 32. diagram_04-search

**CoS · beyond**

```txt
등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색. 파일이 없는 자산도 포함한다. 상세 정보와 파일 상태는 diagram_01-get tool에서 조회한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류값 전체 일치. 대소문자 무시. 비워 두면 전체 검색.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. 일부 세부 값은 포함되지 않을 수 있다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 10,
      "description": "1..50으로 보정.",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제. 등록 치수는 추정치일 수 있다.",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제.",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제.",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류값 전체 일치. 대소문자 무시. 비워 두면 전체 검색.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. 일부 세부 값은 포함되지 않을 수 있다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 10,
      "description": "1..50으로 보정.",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제. 등록 치수는 추정치일 수 있다.",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제.",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "0 이하이면 치수 필터 해제.",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.",
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_offset": {
            "type": [
              "integer",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 33. drawing_01-apply_style

**CoS · beyond**

```txt
도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 적용. 같은 경로의 기존 레이어도 갱신한다. 같은 이름의 선종류는 기존 정의를 재사용하고 새 선종류는 Almond 선종 매니페스트에서 가져온다. 적용 범위는 레이어와 속성이다.

변경 전 전용 Undo record를 확보하고 실패 시 해당 record를 복구한다. mutation_state는 none·completed·rolled_back·unknown. requires_reconciliation=true면 재시도 전에 실제 문서 상태를 확인한다.

레시피의 review_preparation.print_display가 true이면 적용 성공 시 PrintDisplay 설정 명령을 안내한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "recipe_id": {
      "default": "",
      "description": "drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool에서 확인. 생략 시 파일명 순으로 처음 로드된 레시피 적용.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "recipe_id": {
      "default": "",
      "description": "drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool에서 확인. 생략 시 파일명 순으로 처음 로드된 레시피 적용.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "layers": {
            "items": {
              "properties": {
                "layer_index": {
                  "type": "integer"
                },
                "linetype": {
                  "type": "string"
                },
                "path": {
                  "description": "inspect_02-get_objects tool의 layer_paths 필터에 재사용 가능.",
                  "type": "string"
                },
                "plot_weight_mm": {
                  "type": "number"
                },
                "role": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "recipe_id": {
            "type": "string"
          },
          "requires_reconciliation": {
            "description": "true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.",
            "type": "boolean"
          },
          "review_preparation": {
            "properties": {
              "cli": {
                "properties": {
                  "arguments_template": {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "discovery_arguments": {
                    "description": "실행 파이프 확인에 사용할 인수.",
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "program": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "message": {
                "description": "이 연결의 Rhino PID와 문서 경로로 실행 파이프 확인.",
                "type": "string"
              },
              "status": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 34. drawing_02-get_recipe

**CoS · beyond**

```txt
도면 스타일 레시피 조회. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scales, parameters, source, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "recipe_id": {
      "description": "이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool에서 include_ids=true로 조회한 ID.",
      "type": "string"
    }
  },
  "required": [
    "recipe_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scales, parameters, source, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "recipe_id": {
      "description": "이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool에서 include_ids=true로 조회한 ID.",
      "type": "string"
    }
  },
  "required": [
    "recipe_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "recipe": {
            "properties": {
              "description": {
                "type": "string"
              },
              "name": {
                "type": "string"
              },
              "projection": {
                "properties": {
                  "type": {
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 35. drawing_04-import_hatches

**CoS · beyond**

```txt
등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져오기. 같은 이름이 있으면 기존 정의 재사용. 적용 범위는 해치 패턴 정의.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "asset_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "error_trace": {},
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "patterns": {
            "description": "새로 가져온 패턴과 재사용한 기존 패턴 모두 포함.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 36. drawing_05-list_recipes

**CoS · beyond**

```txt
로드된 도면 스타일 레시피 목록. include_ids=true로 얻은 recipe_id는 drawing_02-get_recipe tool과 drawing_01-apply_style tool에서 사용.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scales, parameters, source, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scales, parameters, source, audit, all. 생략하거나 비우면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "recipes": {
            "items": {
              "properties": {
                "description": {
                  "type": [
                    "string",
                    "null"
                  ]
                },
                "name": {
                  "type": [
                    "string",
                    "null"
                  ]
                },
                "projection": {
                  "type": [
                    "string",
                    "null"
                  ]
                },
                "recipe_id": {
                  "type": "string"
                },
                "recommended_scales": {
                  "description": "축척 1:N의 분모 N",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 37. drawing_06-generate_plan_section

**CoS · beyond**

```txt
활성 모델이나 Worksession 첨부 파일의 클리핑 평면에서 단면선·가시 입면선·해치를 생성. Update는 저장 위치에서 다시 계산해 수동 편집을 교체할 수 있고, Move는 GUID와 수동 편집을 유지한 채 원점만 이동.

Rhino는 작업 시작 120초에 취소를 요청한다. 안전한 지점에서 중단하고 Undo와 정리를 마치면 timeout 및 클리핑별 결과를 반환한다. 완료된 도면은 남는다. SDK 호출 또는 정리 중 클라이언트 대기가 끝나면 중단 여부는 미확인이다. 변경 실패 시 객체·속성·레이어 복구 시도는 recovery.attempts에 기록하며 tracked_changes_restored는 추적한 변경의 복구 결과다. requires_reconciliation=true이면 실제 도면과 Undo 상태를 확인하고 자동 재시도하지 않는다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "clipping_ids": {
      "description": "활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "far_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 45.0,
      "description": "먼 입면선 농도(%). 0..100, near_dark 이하."
    },
    "far_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.04,
      "description": "먼 입면선 두께(mm). 양수, near_width 이하."
    },
    "hatch": {
      "default": true,
      "description": "원본 단면 스타일의 채움과 형상 조건에 따라 해치 생성",
      "type": "boolean"
    },
    "include_attachments": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Worksession 첨부 형상 포함. Create에서 생략하면 활성 모델만, Update에서 생략하면 저장된 설정 사용. Move에는 적용되지 않음."
    },
    "near_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 80.0,
      "description": "가까운 입면선 농도(%). 0..100, far_dark 이상."
    },
    "near_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.09,
      "description": "가까운 입면선 두께(mm). 양수, far_width 이상."
    },
    "operation": {
      "description": "Create: 생성 또는 교체. Update: 저장 위치에서 재생성. Move: 기존 도면의 평행이동.",
      "enum": [
        "Create",
        "Update",
        "Move"
      ],
      "type": "string"
    },
    "points": {
      "anyOf": [
        {
          "additionalProperties": {
            "items": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략."
    },
    "small_details": {
      "default": false,
      "description": "입면 투영에서 작은 상세 보호",
      "type": "boolean"
    }
  },
  "required": [
    "operation",
    "clipping_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "clipping_ids": {
      "description": "활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "far_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 45.0,
      "description": "먼 입면선 농도(%). 0..100, near_dark 이하."
    },
    "far_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.04,
      "description": "먼 입면선 두께(mm). 양수, near_width 이하."
    },
    "hatch": {
      "default": true,
      "description": "원본 단면 스타일의 채움과 형상 조건에 따라 해치 생성",
      "type": "boolean"
    },
    "include_attachments": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Worksession 첨부 형상 포함. Create에서 생략하면 활성 모델만, Update에서 생략하면 저장된 설정 사용. Move에는 적용되지 않음."
    },
    "near_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 80.0,
      "description": "가까운 입면선 농도(%). 0..100, far_dark 이상."
    },
    "near_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.09,
      "description": "가까운 입면선 두께(mm). 양수, far_width 이상."
    },
    "operation": {
      "description": "Create: 생성 또는 교체. Update: 저장 위치에서 재생성. Move: 기존 도면의 평행이동.",
      "enum": [
        "Create",
        "Update",
        "Move"
      ],
      "type": "string"
    },
    "points": {
      "anyOf": [
        {
          "additionalProperties": {
            "items": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략."
    },
    "small_details": {
      "default": false,
      "description": "입면 투영에서 작은 상세 보호",
      "type": "boolean"
    }
  },
  "required": [
    "operation",
    "clipping_ids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "drawing_status": {
            "description": "completed, partial, cancelled, failed",
            "type": "string"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "type": "string"
          },
          "next_step_guide": {
            "description": "도면 확인 또는 중단·미완료 범위 확인 안내",
            "type": "string"
          },
          "recovery": {
            "description": "복구가 필요했던 클리핑별 오류와 보상 내역",
            "items": {
              "properties": {
                "clipping_id": {
                  "type": "string"
                },
                "error": {
                  "description": "복구 시도 전 최초 변경 실패 원문",
                  "type": "string"
                },
                "recovery": {
                  "description": "추적한 변경에 대한 보상 결과. 성공해도 원자적 롤백은 보장되지 않음.",
                  "properties": {
                    "attempts": {
                      "items": {
                        "properties": {
                          "action": {
                            "type": "string"
                          },
                          "error": {
                            "type": "string"
                          },
                          "status": {
                            "description": "restored 또는 failed",
                            "type": "string"
                          },
                          "target": {
                            "description": "복구 대상 객체·레이어·기록",
                            "type": "string"
                          }
                        },
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "mutation_state": {
                      "description": "보상 실패는 partial, 미확인 변경 가능성이 남으면 unknown",
                      "type": "string"
                    },
                    "requires_reconciliation": {
                      "type": "boolean"
                    },
                    "tracked_changes_restored": {
                      "description": "추적한 변경에 대한 모든 보상 시도의 성공 여부",
                      "type": "boolean"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "requires_reconciliation": {
            "type": "boolean"
          },
          "result": {
            "properties": {
              "completed": {
                "type": "integer"
              },
              "requested": {
                "description": "중복을 제외한 클리핑 요청 수",
                "type": "integer"
              },
              "requires_reconciliation": {
                "type": "boolean"
              },
              "results": {
                "items": {
                  "properties": {
                    "cleanup_error": {
                      "type": "string"
                    },
                    "clipping_id": {
                      "type": "string"
                    },
                    "draw_plane": {
                      "description": "원점과 축으로 표현한 실제 배치 평면",
                      "properties": {
                        "origin": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        },
                        "xaxis": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        },
                        "yaxis": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        }
                      },
                      "type": "object"
                    },
                    "error": {
                      "type": "string"
                    },
                    "extraction": {
                      "description": "Create·Update에서 실제 계산에 사용한 추출 조건",
                      "properties": {
                        "include_attachments": {
                          "description": "Worksession 첨부 형상을 계산 범위에 허용했는지 표시",
                          "type": "boolean"
                        },
                        "include_hidden": {
                          "type": "boolean"
                        },
                        "include_locked": {
                          "type": "boolean"
                        },
                        "layers": {
                          "description": "계산에 사용한 원본 레이어 전체 경로",
                          "items": {
                            "type": "string"
                          },
                          "type": "array"
                        },
                        "source_object_count": {
                          "type": "integer"
                        }
                      },
                      "type": "object"
                    },
                    "mutation_state": {
                      "description": "변경 후 최종 결과 미확인 시 unknown",
                      "type": "string"
                    },
                    "name": {
                      "type": [
                        "string",
                        "null"
                      ]
                    },
                    "object_ids": {
                      "description": "생성·갱신·이동에서 관찰한 객체 GUID. unconfirmed이면 최종 문서에 남았는지 대조 필요",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "recovery": {
                      "description": "추적한 변경에 대한 보상 결과. 성공해도 원자적 롤백은 보장되지 않음.",
                      "properties": {
                        "attempts": {
                          "items": {
                            "properties": {
                              "action": {
                                "type": "string"
                              },
                              "error": {
                                "type": "string"
                              },
                              "status": {
                                "description": "restored 또는 failed",
                                "type": "string"
                              },
                              "target": {
                                "description": "복구 대상 객체·레이어·기록",
                                "type": "string"
                              }
                            },
                            "type": "object"
                          },
                          "type": "array"
                        },
                        "mutation_state": {
                          "description": "보상 실패는 partial, 미확인 변경 가능성이 남으면 unknown",
                          "type": "string"
                        },
                        "requires_reconciliation": {
                          "type": "boolean"
                        },
                        "tracked_changes_restored": {
                          "description": "추적한 변경에 대한 모든 보상 시도의 성공 여부",
                          "type": "boolean"
                        }
                      },
                      "type": "object"
                    },
                    "report": {
                      "description": "계산 단계와 제외·정리한 형상에 대한 기록",
                      "type": "object"
                    },
                    "status": {
                      "enum": [
                        "completed",
                        "failed",
                        "skipped",
                        "cancelled",
                        "not_started",
                        "unconfirmed"
                      ],
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "status": {
                "type": "string"
              },
              "stop_reason": {
                "description": "알고리즘이 안전한 지점에서 관찰한 취소 사유",
                "enum": [
                  "deadline",
                  "user"
                ],
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "description": "success, partial, cancelled(사용자 취소), timeout(120초 취소 후 중단·정리 확인), error",
            "type": "string"
          },
          "unconfirmed_clipping_ids": {
            "description": "최종 변경 상태를 확인할 수 없는 클리핑 GUID",
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 38. grasshopper_01-get_logic

**CoS · beyond**

```txt
색인된 Grasshopper 로직에서 물리 관련 컴포넌트, 설명, 메타데이터를 추출해 조회. JSON만 있는 항목은 메타데이터만 제공. 구성·연결 관계의 완전성과 실행 가능성은 별도 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "ports, definition, source, paths, audit, all. 제공된 필드에만 적용."
    },
    "include_ids": {
      "default": false,
      "description": "추가 식별자 포함. 입력 logic_id는 반복하지 않음.",
      "type": "boolean"
    },
    "logic_id": {
      "description": "확장자를 뺀 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.",
      "type": "string"
    }
  },
  "required": [
    "logic_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "ports, definition, source, paths, audit, all. 제공된 필드에만 적용."
    },
    "include_ids": {
      "default": false,
      "description": "추가 식별자 포함. 입력 logic_id는 반복하지 않음.",
      "type": "boolean"
    },
    "logic_id": {
      "description": "확장자를 뺀 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.",
      "type": "string"
    }
  },
  "required": [
    "logic_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "all_descriptions": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "components": {
            "items": {
              "properties": {
                "category": {
                  "type": "string"
                },
                "descriptions": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "name": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "file_name": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "metadata": {
            "properties": {},
            "type": "object"
          },
          "next_step_guide": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 39. grasshopper_02-list_capsules

**CoS · beyond**

```txt
등록된 Grasshopper 캡슐의 기능과 실행 감사 상태를 조회. 포트와 ID는 grasshopper_04-run_definition tool의 입력에 사용. 감사 상태와 정의 파일의 존재·실행 성공은 별개.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "audited_only": {
      "default": false,
      "type": "boolean"
    },
    "capability": {
      "default": "",
      "description": "analyze, generate, form_find, aggregate. 대소문자 구분 없음.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "ports, definition, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "description": "capsule_id 포함. all과 별도 지정.",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "audited_only": {
      "default": false,
      "type": "boolean"
    },
    "capability": {
      "default": "",
      "description": "analyze, generate, form_find, aggregate. 대소문자 구분 없음.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "ports, definition, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "description": "capsule_id 포함. all과 별도 지정.",
      "type": "boolean"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "capsules": {
            "items": {
              "properties": {
                "audited": {
                  "type": "boolean"
                },
                "capability": {
                  "type": "string"
                },
                "capsule_id": {
                  "description": "audited=true인 캡슐을 grasshopper_04-run_definition tool에 지정",
                  "type": "string"
                },
                "definition_file": {
                  "description": "캡슐 라이브러리 기준 정의 파일명",
                  "type": "string"
                },
                "input_ports": {
                  "items": {
                    "properties": {
                      "description": {
                        "type": "string"
                      },
                      "name": {
                        "description": "grasshopper_04-run_definition tool에서 inputs의 키로 사용",
                        "type": "string"
                      },
                      "required": {
                        "description": "true 또는 생략이면 입력 필수",
                        "type": "boolean"
                      },
                      "type": {
                        "description": "[] 접미사는 해당 타입의 배열",
                        "type": "string"
                      },
                      "units": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                },
                "inputs": {
                  "description": "타입·단위·필수 여부는 input_ports 참조",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "output_ports": {
                  "items": {
                    "properties": {
                      "description": {
                        "type": "string"
                      },
                      "name": {
                        "description": "grasshopper_04-run_definition tool의 outputs에서 이 이름을 키로 사용",
                        "type": "string"
                      },
                      "type": {
                        "description": "[] 접미사는 해당 타입의 배열",
                        "type": "string"
                      },
                      "units": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                },
                "outputs": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "structure_type": {
                  "type": [
                    "string",
                    "null"
                  ]
                },
                "title": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_offset": {
            "type": [
              "integer",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 40. grasshopper_03-list_library

**CoS · beyond**

```txt
로컬 Grasshopper 라이브러리의 색인된 로직 목록. logic_names는 grasshopper_01-get_logic tool에서 조회할 때 사용.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "paths·all은 라이브러리 경로 포함. ports·definition·source·audit은 목록에 적용되지 않음."
    },
    "include_ids": {
      "default": false,
      "description": "logic_names와 같은 값의 logic_ids 포함",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "paths·all은 라이브러리 경로 포함. ports·definition·source·audit은 목록에 적용되지 않음."
    },
    "include_ids": {
      "default": false,
      "description": "logic_names와 같은 값의 logic_ids 포함",
      "type": "boolean"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "logic_count": {
            "description": "include_ids=false일 때 logic_ids 대신 반환",
            "type": "number"
          },
          "logic_names": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "total_entries": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 41. grasshopper_04-run_definition

**CoS · beyond**

```txt
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산. 모든 출력 포트를 확인한 뒤 정의에 따라 하나의 Undo 기록으로 형상 베이크. mutation_state는 none·completed·rolled_back·unknown. requires_reconciliation=true이면 자동 재시도 금지. baked_guids와 현재 문서 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "capsule_id": {
      "description": "grasshopper_02-list_capsules tool에서 얻은 캡슐 ID. 예: karamba_beam_v1.",
      "type": "string"
    },
    "inputs": {
      "additionalProperties": true,
      "description": "ALMOND_IN_ 포트 이름을 키로 사용. grasshopper_02-list_capsules tool의 field_groups=['ports']로 input_ports의 타입·단위·필수 여부 확인. 형상은 {\"guids\":[\"객체 GUID\"]}, 숫자·정수·문자열·불리언은 JSON 값, number[]·integer[]·string[]은 평탄한 배열.",
      "type": "object"
    },
    "seed": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "확률적 정의에만 정수 시드 사용"
    },
    "timeout_s": {
      "default": 60.0,
      "description": "솔버 시간 한도(초). 0 초과, 600 이하.",
      "type": "number"
    }
  },
  "required": [
    "capsule_id",
    "inputs"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "capsule_id": {
      "description": "grasshopper_02-list_capsules tool에서 얻은 캡슐 ID. 예: karamba_beam_v1.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "inputs": {
      "additionalProperties": true,
      "description": "ALMOND_IN_ 포트 이름을 키로 사용. grasshopper_02-list_capsules tool의 field_groups=['ports']로 input_ports의 타입·단위·필수 여부 확인. 형상은 {\"guids\":[\"객체 GUID\"]}, 숫자·정수·문자열·불리언은 JSON 값, number[]·integer[]·string[]은 평탄한 배열.",
      "type": "object"
    },
    "seed": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "확률적 정의에만 정수 시드 사용"
    },
    "timeout_s": {
      "default": 60.0,
      "description": "솔버 시간 한도(초). 0 초과, 600 이하.",
      "type": "number"
    }
  },
  "required": [
    "capsule_id",
    "inputs",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "analysis_method": {
            "type": "string"
          },
          "available_capsules": {
            "description": "알 수 없는 capsule_id를 요청했을 때 반환. 실행 감사 상태는 grasshopper_02-list_capsules tool의 audited 참조.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "baked_guids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "capsule_id": {
            "type": "string"
          },
          "confidence": {
            "description": "매니페스트 선언 기준: api/high, template/medium, rule_based/low",
            "type": "string"
          },
          "error": {},
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "outputs": {
            "description": "값의 의미·타입·단위는 캡슐 포트 계약을 따름",
            "properties": {},
            "type": "object"
          },
          "requires_reconciliation": {
            "description": "true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.",
            "type": "boolean"
          },
          "status": {
            "type": "string"
          },
          "valid_inputs": {
            "description": "입력 검증 실패 시 반환. 타입·단위·필수 여부는 grasshopper_02-list_capsules tool의 input_ports 참조.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 42. inspect_01-analyze_nested_blocks

**CoS · beyond**

```txt
읽기 전용 중첩 블록 조회. outline은 선택된 루트를 기본으로 구조를 요약하고, resolve-block은 루트부터 대상까지의 경로로 공유 배치와 참조·링크 제한을 확인.

definition_impact.complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부. 정의 내부 ID는 편집 가능한 문서 객체 ID와 다를 수 있다. 후속 조회에 ID가 필요하면 include_ids=true 사용.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "mode": {
      "description": "outline 또는 resolve-block",
      "type": "string"
    },
    "options": {
      "additionalProperties": true,
      "description": "outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.\ndepth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).\nfield_groups: summary(기본), objects, annotations, transforms. include_geometry와 annotations로 형상·주석 포함, annotation_layer로 TextDot 레이어 필터링. field_groups를 생략하고 include_geometry 또는 annotations를 지정하면 기존 상세 모드.\nresolve-block: path에 최상위부터 대상 블록까지 GUID 1..65개.",
      "type": "object"
    }
  },
  "required": [
    "mode",
    "options"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "mode": {
      "description": "outline 또는 resolve-block",
      "type": "string"
    },
    "options": {
      "additionalProperties": true,
      "description": "outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.\ndepth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).\nfield_groups: summary(기본), objects, annotations, transforms. include_geometry와 annotations로 형상·주석 포함, annotation_layer로 TextDot 레이어 필터링. field_groups를 생략하고 include_geometry 또는 annotations를 지정하면 기존 상세 모드.\nresolve-block: path에 최상위부터 대상 블록까지 GUID 1..65개.",
      "type": "object"
    }
  },
  "required": [
    "mode",
    "options",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "data": {
            "properties": {
              "items": {
                "type": "integer"
              },
              "records": {
                "description": "블록 배치 또는 정의별 분석 항목",
                "items": {
                  "properties": {
                    "definition": {
                      "type": "string"
                    },
                    "id": {
                      "description": "배치 객체 또는 정의 구성원의 ID. 편집 가능한 문서 객체 ID는 inspect_02-get_objects tool로 확인.",
                      "type": "string"
                    },
                    "kind": {
                      "type": "string"
                    },
                    "path": {
                      "description": "공유 정의 영향을 조회할 때 resolve-block의 options.path에 재사용",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "type": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "truncated": {
                "type": "boolean"
              }
            },
            "type": "object"
          },
          "document": {
            "properties": {
              "absolute_tolerance": {
                "description": "문서 길이 단위",
                "type": "number"
              },
              "units": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mode": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 43. inspect_02-get_objects

**CoS · beyond**

```txt
GUID를 몰라도 레이어·이름·객체 유형·그룹·메타데이터 조건으로 Rhino 최상위 모델 객체를 찾고 후속 호출에 쓸 GUID를 조회. Rhino의 선택 상태는 변경하지 않음. current는 표시되고 잠기지 않은 객체(화면 밖 포함), document는 숨김·잠금 객체까지 포함. 그룹은 선택 범위와 구성원의 교집합. 계층 모드는 그룹·블록 배치를 펼쳐 문서 객체와 블록 정의 내부 항목을 구분. 표시 여부는 가림을 고려한 화면 가시성과 별개.

활성 뷰포트의 벽 레이어 객체 GUID 조회 예: `{"scope":"inside_viewport","filters":{"layer":{"include":["2F::Wall"]}},"output":{"include_ids":true}}`.
UserDictionary 조건 예: `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`.

행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을 사용. 면 후속 조회에는 document 객체 ID와 geometry_crc 사용. objects·summary의 complete는 전체 행이 첫 응답에 포함되고 편집 상태가 안정적일 때 true. hierarchy는 관계 완전성도 확인하며 깊이 제한을 적용할 수 있다. face_page.complete는 전체 면이 첫 응답에 포함됐을 때 true. 마지막 행 페이지는 next_offset=null.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "default": 1,
      "description": "1..8, 루트=1. 1 초과 시 recursive=true.",
      "type": "integer"
    },
    "expected_geometry_crcs": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "integer"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부."
    },
    "expected_model_path": {
      "default": "",
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "expected_snapshot": {
      "default": "",
      "description": "offset > 0이면 첫 페이지의 snapshot 필요",
      "type": "string"
    },
    "face_limit": {
      "default": 128,
      "description": "1..128. objects 모드에서 사용.",
      "type": "integer"
    },
    "face_offset": {
      "default": 0,
      "description": "양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요",
      "type": "integer"
    },
    "fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1개 이상 선택: id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count. 형상 상세와 faces는 objects 모드에서만 사용. summary에서는 fields 지정 불가."
    },
    "filters": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "block": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "group": {
              "additionalProperties": false,
              "allOf": [
                {
                  "else": {
                    "not": {
                      "required": [
                        "include_mode"
                      ]
                    }
                  },
                  "if": {
                    "properties": {
                      "include": {
                        "minItems": 2
                      }
                    },
                    "required": [
                      "include"
                    ]
                  },
                  "then": {
                    "required": [
                      "include_mode"
                    ]
                  }
                },
                {
                  "else": {
                    "not": {
                      "required": [
                        "exclude_mode"
                      ]
                    }
                  },
                  "if": {
                    "properties": {
                      "exclude": {
                        "minItems": 2
                      }
                    },
                    "required": [
                      "exclude"
                    ]
                  },
                  "then": {
                    "required": [
                      "exclude_mode"
                    ]
                  }
                }
              ],
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "exclude_mode": {
                  "enum": [
                    "any",
                    "all"
                  ],
                  "type": "string"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include_mode": {
                  "enum": [
                    "any",
                    "all"
                  ],
                  "type": "string"
                }
              },
              "type": "object"
            },
            "layer": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "layer_paths": {
              "items": {
                "minLength": 1,
                "type": "string"
              },
              "maxItems": 64,
              "minItems": 1,
              "type": "array"
            },
            "material": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "name": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "name_contains": {
              "maxLength": 256,
              "type": "string"
            },
            "object_type": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "object_types": {
              "items": {
                "maxLength": 64,
                "minLength": 1,
                "type": "string"
              },
              "maxItems": 32,
              "minItems": 1,
              "type": "array"
            },
            "user_dictionary": {
              "anyOf": [
                {
                  "items": {
                    "additionalProperties": false,
                    "properties": {
                      "any_of": {
                        "items": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "type": "boolean"
                            },
                            {
                              "type": "integer"
                            },
                            {
                              "type": "number"
                            }
                          ]
                        },
                        "maxItems": 64,
                        "minItems": 1,
                        "type": "array"
                      },
                      "key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "source": {
                        "enum": [
                          "attributes",
                          "geometry"
                        ],
                        "type": "string"
                      }
                    },
                    "required": [
                      "source",
                      "key",
                      "any_of"
                    ],
                    "type": "object"
                  },
                  "maxItems": 16,
                  "type": "array"
                },
                {
                  "additionalProperties": false,
                  "minProperties": 1,
                  "properties": {
                    "exclude": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "type": "boolean"
                                },
                                {
                                  "type": "integer"
                                },
                                {
                                  "type": "number"
                                }
                              ]
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "source": {
                            "enum": [
                              "attributes",
                              "geometry"
                            ],
                            "type": "string"
                          }
                        },
                        "required": [
                          "source",
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    },
                    "include": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "type": "boolean"
                                },
                                {
                                  "type": "integer"
                                },
                                {
                                  "type": "number"
                                }
                              ]
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "source": {
                            "enum": [
                              "attributes",
                              "geometry"
                            ],
                            "type": "string"
                          }
                        },
                        "required": [
                          "source",
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              ]
            },
            "user_text": {
              "anyOf": [
                {
                  "items": {
                    "additionalProperties": false,
                    "properties": {
                      "any_of": {
                        "items": {
                          "type": "string"
                        },
                        "maxItems": 64,
                        "minItems": 1,
                        "type": "array"
                      },
                      "key": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "key",
                      "any_of"
                    ],
                    "type": "object"
                  },
                  "maxItems": 16,
                  "type": "array"
                },
                {
                  "additionalProperties": false,
                  "minProperties": 1,
                  "properties": {
                    "exclude": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "type": "string"
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          }
                        },
                        "required": [
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    },
                    "include": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "type": "string"
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          }
                        },
                        "required": [
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              ]
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 조건은 함께 적용. layer는 전체 경로/GUID, block은 배치의 정의 이름/GUID, group은 멤버십 이름/GUID, material은 배치 객체 전면의 실효 재질 이름/GUID(레이어 상속 포함), name은 객체 이름 정확 일치, object_type은 Rhino 유형명. 이름 비교는 대소문자 무시. 단일값 속성은 include 중 하나에 해당하고 exclude에 없어야 함. group의 include·exclude는 각각 1..64개. 두 개 이상 지정한 쪽에만 include_mode·exclude_mode로 any(하나 이상) 또는 all(모두)을 명시. exclude는 그 조건에 해당하면 제외. user_text·user_dictionary의 include·exclude는 각각 한 조건. 메타데이터는 조건 객체 1개도 배열로 지정. 기존 조건 배열은 최대 16개 조건을 모두 만족해야 함. 각 any_of는 값 하나와 일치하면 충족. 기존 layer_paths·object_types·name_contains(부분 문자열) 사용 가능."
    },
    "group_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가."
    },
    "include_geometry": {
      "default": false,
      "description": "fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.",
      "type": "boolean"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "inside_window": {
      "default": false,
      "description": "current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.",
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1..200",
      "type": "integer"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가."
    },
    "offset": {
      "default": 0,
      "description": "0..100000. 양수이면 expected_snapshot 필요.",
      "type": "integer"
    },
    "output": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "expected_snapshot": {
              "type": "string"
            },
            "fields": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "include_geometry": {
              "type": "boolean"
            },
            "include_ids": {
              "type": "boolean"
            },
            "limit": {
              "maximum": 200,
              "minimum": 1,
              "type": "integer"
            },
            "offset": {
              "maximum": 100000,
              "minimum": 0,
              "type": "integer"
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "fields·include_ids·include_geometry·limit·offset·expected_snapshot 중 필요한 항목. 같은 이름의 평면 인자도 지정하면 output 값이 우선."
    },
    "recursive": {
      "default": false,
      "description": "true이면 계층 모드 사용",
      "type": "boolean"
    },
    "result_mode": {
      "default": "objects",
      "description": "objects, hierarchy, summary. recursive=true와 summary는 동시 지정 불가.",
      "enum": [
        "objects",
        "hierarchy",
        "summary"
      ],
      "type": "string"
    },
    "scope": {
      "default": "current",
      "description": "current, document 또는 inside_viewport. inside_viewport는 current 중 활성 모델 뷰 또는 Detail 경계와 바운딩 박스가 교차하는 객체. 가림과 클리핑 평면은 판정하지 않음.",
      "enum": [
        "current",
        "document",
        "inside_viewport"
      ],
      "type": "string"
    },
    "selected": {
      "default": false,
      "description": "current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "default": 1,
      "description": "1..8, 루트=1. 1 초과 시 recursive=true.",
      "type": "integer"
    },
    "expected_geometry_crcs": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "integer"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부."
    },
    "expected_model_path": {
      "default": "",
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "expected_snapshot": {
      "default": "",
      "description": "offset > 0이면 첫 페이지의 snapshot 필요",
      "type": "string"
    },
    "face_limit": {
      "default": 128,
      "description": "1..128. objects 모드에서 사용.",
      "type": "integer"
    },
    "face_offset": {
      "default": 0,
      "description": "양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요",
      "type": "integer"
    },
    "fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1개 이상 선택: id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count. 형상 상세와 faces는 objects 모드에서만 사용. summary에서는 fields 지정 불가."
    },
    "filters": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "block": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "group": {
              "additionalProperties": false,
              "allOf": [
                {
                  "else": {
                    "not": {
                      "required": [
                        "include_mode"
                      ]
                    }
                  },
                  "if": {
                    "properties": {
                      "include": {
                        "minItems": 2
                      }
                    },
                    "required": [
                      "include"
                    ]
                  },
                  "then": {
                    "required": [
                      "include_mode"
                    ]
                  }
                },
                {
                  "else": {
                    "not": {
                      "required": [
                        "exclude_mode"
                      ]
                    }
                  },
                  "if": {
                    "properties": {
                      "exclude": {
                        "minItems": 2
                      }
                    },
                    "required": [
                      "exclude"
                    ]
                  },
                  "then": {
                    "required": [
                      "exclude_mode"
                    ]
                  }
                }
              ],
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "exclude_mode": {
                  "enum": [
                    "any",
                    "all"
                  ],
                  "type": "string"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include_mode": {
                  "enum": [
                    "any",
                    "all"
                  ],
                  "type": "string"
                }
              },
              "type": "object"
            },
            "layer": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "layer_paths": {
              "items": {
                "minLength": 1,
                "type": "string"
              },
              "maxItems": 64,
              "minItems": 1,
              "type": "array"
            },
            "material": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "name": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "name_contains": {
              "maxLength": 256,
              "type": "string"
            },
            "object_type": {
              "additionalProperties": false,
              "minProperties": 1,
              "properties": {
                "exclude": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                },
                "include": {
                  "items": {
                    "minLength": 1,
                    "type": "string"
                  },
                  "maxItems": 64,
                  "minItems": 1,
                  "type": "array"
                }
              },
              "type": "object"
            },
            "object_types": {
              "items": {
                "maxLength": 64,
                "minLength": 1,
                "type": "string"
              },
              "maxItems": 32,
              "minItems": 1,
              "type": "array"
            },
            "user_dictionary": {
              "anyOf": [
                {
                  "items": {
                    "additionalProperties": false,
                    "properties": {
                      "any_of": {
                        "items": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "type": "boolean"
                            },
                            {
                              "type": "integer"
                            },
                            {
                              "type": "number"
                            }
                          ]
                        },
                        "maxItems": 64,
                        "minItems": 1,
                        "type": "array"
                      },
                      "key": {
                        "minLength": 1,
                        "type": "string"
                      },
                      "source": {
                        "enum": [
                          "attributes",
                          "geometry"
                        ],
                        "type": "string"
                      }
                    },
                    "required": [
                      "source",
                      "key",
                      "any_of"
                    ],
                    "type": "object"
                  },
                  "maxItems": 16,
                  "type": "array"
                },
                {
                  "additionalProperties": false,
                  "minProperties": 1,
                  "properties": {
                    "exclude": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "type": "boolean"
                                },
                                {
                                  "type": "integer"
                                },
                                {
                                  "type": "number"
                                }
                              ]
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "source": {
                            "enum": [
                              "attributes",
                              "geometry"
                            ],
                            "type": "string"
                          }
                        },
                        "required": [
                          "source",
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    },
                    "include": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "type": "boolean"
                                },
                                {
                                  "type": "integer"
                                },
                                {
                                  "type": "number"
                                }
                              ]
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          },
                          "source": {
                            "enum": [
                              "attributes",
                              "geometry"
                            ],
                            "type": "string"
                          }
                        },
                        "required": [
                          "source",
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              ]
            },
            "user_text": {
              "anyOf": [
                {
                  "items": {
                    "additionalProperties": false,
                    "properties": {
                      "any_of": {
                        "items": {
                          "type": "string"
                        },
                        "maxItems": 64,
                        "minItems": 1,
                        "type": "array"
                      },
                      "key": {
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "key",
                      "any_of"
                    ],
                    "type": "object"
                  },
                  "maxItems": 16,
                  "type": "array"
                },
                {
                  "additionalProperties": false,
                  "minProperties": 1,
                  "properties": {
                    "exclude": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "type": "string"
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          }
                        },
                        "required": [
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    },
                    "include": {
                      "items": {
                        "additionalProperties": false,
                        "properties": {
                          "any_of": {
                            "items": {
                              "type": "string"
                            },
                            "maxItems": 64,
                            "minItems": 1,
                            "type": "array"
                          },
                          "key": {
                            "minLength": 1,
                            "type": "string"
                          }
                        },
                        "required": [
                          "key",
                          "any_of"
                        ],
                        "type": "object"
                      },
                      "maxItems": 1,
                      "minItems": 1,
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              ]
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 조건은 함께 적용. layer는 전체 경로/GUID, block은 배치의 정의 이름/GUID, group은 멤버십 이름/GUID, material은 배치 객체 전면의 실효 재질 이름/GUID(레이어 상속 포함), name은 객체 이름 정확 일치, object_type은 Rhino 유형명. 이름 비교는 대소문자 무시. 단일값 속성은 include 중 하나에 해당하고 exclude에 없어야 함. group의 include·exclude는 각각 1..64개. 두 개 이상 지정한 쪽에만 include_mode·exclude_mode로 any(하나 이상) 또는 all(모두)을 명시. exclude는 그 조건에 해당하면 제외. user_text·user_dictionary의 include·exclude는 각각 한 조건. 메타데이터는 조건 객체 1개도 배열로 지정. 기존 조건 배열은 최대 16개 조건을 모두 만족해야 함. 각 any_of는 값 하나와 일치하면 충족. 기존 layer_paths·object_types·name_contains(부분 문자열) 사용 가능."
    },
    "group_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가."
    },
    "include_geometry": {
      "default": false,
      "description": "fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.",
      "type": "boolean"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "inside_window": {
      "default": false,
      "description": "current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.",
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1..200",
      "type": "integer"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가."
    },
    "offset": {
      "default": 0,
      "description": "0..100000. 양수이면 expected_snapshot 필요.",
      "type": "integer"
    },
    "output": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "expected_snapshot": {
              "type": "string"
            },
            "fields": {
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "include_geometry": {
              "type": "boolean"
            },
            "include_ids": {
              "type": "boolean"
            },
            "limit": {
              "maximum": 200,
              "minimum": 1,
              "type": "integer"
            },
            "offset": {
              "maximum": 100000,
              "minimum": 0,
              "type": "integer"
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "fields·include_ids·include_geometry·limit·offset·expected_snapshot 중 필요한 항목. 같은 이름의 평면 인자도 지정하면 output 값이 우선."
    },
    "recursive": {
      "default": false,
      "description": "true이면 계층 모드 사용",
      "type": "boolean"
    },
    "result_mode": {
      "default": "objects",
      "description": "objects, hierarchy, summary. recursive=true와 summary는 동시 지정 불가.",
      "enum": [
        "objects",
        "hierarchy",
        "summary"
      ],
      "type": "string"
    },
    "scope": {
      "default": "current",
      "description": "current, document 또는 inside_viewport. inside_viewport는 current 중 활성 모델 뷰 또는 Detail 경계와 바운딩 박스가 교차하는 객체. 가림과 클리핑 평면은 판정하지 않음.",
      "enum": [
        "current",
        "document",
        "inside_viewport"
      ],
      "type": "string"
    },
    "selected": {
      "default": false,
      "description": "current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.",
      "type": "boolean"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "complete": {
            "description": "계층 하위의 관찰 상태는 각 children_state 참조",
            "type": "boolean"
          },
          "editing": {
            "description": "편집 컨텍스트와 저장 대상",
            "properties": {},
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "matched_count": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_offset": {
            "type": [
              "integer",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "nodes": {
            "items": {
              "properties": {
                "user_text": {
                  "description": "Rhino 객체 속성의 User Text",
                  "properties": {
                    "total_keys": {
                      "description": "응답 제한을 적용하기 전 저장된 키 수",
                      "type": "integer"
                    },
                    "truncated": {
                      "type": "boolean"
                    },
                    "values": {
                      "description": "저장된 문자열이나 응답 제한으로 생략된 값의 표시",
                      "type": "object"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "objects": {
            "items": {
              "properties": {
                "face_count": {
                  "type": "integer"
                },
                "face_page": {
                  "properties": {
                    "complete": {
                      "type": "boolean"
                    },
                    "limit": {
                      "type": "integer"
                    },
                    "next_offset": {
                      "type": [
                        "integer",
                        "null"
                      ]
                    },
                    "offset": {
                      "type": "integer"
                    },
                    "returned": {
                      "type": "integer"
                    }
                  },
                  "type": "object"
                },
                "faces": {
                  "items": {
                    "properties": {
                      "face_edit_supported": {
                        "description": "기본 편집 조건만 확인한 값. 실제 편집 전에 형상 버전을 다시 검사.",
                        "type": "boolean"
                      },
                      "face_index": {
                        "description": "같은 관찰의 id·geometry_crc와 묶어 model_02-edit_planar_face tool의 object_id·face_index·expected_geometry_crc에 전달",
                        "type": "number"
                      },
                      "planar": {
                        "type": "boolean"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                },
                "faces_truncated": {
                  "type": "boolean"
                },
                "geometry_crc": {
                  "description": "면 편집과 후속 면 조회에 사용할 형상 버전",
                  "type": "number"
                },
                "id": {
                  "type": "string"
                },
                "user_text": {
                  "description": "Rhino 객체 속성의 User Text",
                  "properties": {
                    "total_keys": {
                      "description": "응답 제한을 적용하기 전 저장된 키 수",
                      "type": "integer"
                    },
                    "truncated": {
                      "type": "boolean"
                    },
                    "values": {
                      "description": "저장된 문자열이나 응답 제한으로 생략된 값의 표시",
                      "type": "object"
                    }
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "offset": {
            "type": "integer"
          },
          "scope": {
            "type": "string"
          },
          "snapshot": {
            "description": "후속 행 조회의 expected_snapshot에 그대로 전달",
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 44. inspect_03-get_document_context

**CoS · beyond**

```txt
연결된 Rhino 문서·뷰·편집 상태와 Named View·Layout·레이어 계층·뷰 메뉴의 표시 모드 조회. Named View·Layout·표시 모드는 목록별 최대 128개이며 include_ids와 무관하게 ID를 반환. 화면 캡처에는 capture_03-current_view tool 사용.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_editor_details": {
      "default": false,
      "description": "editor 요청 시 공급자·명령·Undo 근거 포함",
      "type": "boolean"
    },
    "include_ids": {
      "default": false,
      "description": "뷰포트 등 선택적으로 ID를 반환하는 항목에 적용",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택. 생략 또는 null이면 document, named_views, layouts, layer_tree, display_modes. []이면 항목 조회 생략."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_editor_details": {
      "default": false,
      "description": "editor 요청 시 공급자·명령·Undo 근거 포함",
      "type": "boolean"
    },
    "include_ids": {
      "default": false,
      "description": "뷰포트 등 선택적으로 ID를 반환하는 항목에 적용",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택. 생략 또는 null이면 document, named_views, layouts, layer_tree, display_modes. []이면 항목 조회 생략."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "document": {
            "properties": {
              "absolute_tolerance": {
                "description": "문서 길이 단위",
                "type": [
                  "number",
                  "null"
                ]
              },
              "angle_tolerance": {
                "description": "라디안",
                "type": [
                  "number",
                  "null"
                ]
              },
              "layer_count": {
                "type": [
                  "number",
                  "null"
                ]
              },
              "modified": {
                "type": [
                  "boolean",
                  "null"
                ]
              },
              "object_count": {
                "type": [
                  "integer",
                  "null"
                ]
              },
              "units": {
                "type": [
                  "string",
                  "null"
                ]
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "layer_tree": {
            "type": [
              "string",
              "null"
            ]
          },
          "layouts": {
            "items": {
              "properties": {
                "id": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": [
              "array",
              "null"
            ]
          },
          "message": {
            "type": "string"
          },
          "named_views": {
            "items": {
              "properties": {
                "id": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": [
              "array",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 45. inspect_04-get_selection_references

**CoS · beyond**

```txt
저장된 Rhino 문서의 일반 모델에서 선택 객체의 소속 Holon과 상위 Holon을 참조하는 Plan 조회. 일치한 Holon과 Plan의 전체 대상은 다를 수 있다. selection_truncated는 선택 목록, truncated는 Plan 목록에 적용.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "limit": {
      "default": 50,
      "description": "반환할 Plan 수 1..500",
      "type": "integer"
    },
    "selection_limit": {
      "default": 50,
      "description": "검사할 선택 객체 수 1..200",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "limit": {
      "default": 50,
      "description": "반환할 Plan 수 1..500",
      "type": "integer"
    },
    "selection_limit": {
      "default": 50,
      "description": "검사할 선택 객체 수 1..200",
      "type": "integer"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holons": {
            "description": "선택 객체를 소유한 Holon과 상위 Holon",
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "objects": {
            "description": "선택 객체의 등록 여부와 소유 Holon 포함",
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "ownership_live_verified": {
            "description": "현재 Rhino에서 소유 관계를 확인한 결과. 선택이 없으면 false.",
            "type": "boolean"
          },
          "plans": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "references_live_verified": {
            "description": "저장된 Plan·계층 참조의 현재 Rhino 검증 여부",
            "type": "boolean"
          },
          "selection_total": {
            "type": "integer"
          },
          "selection_truncated": {
            "type": "boolean"
          },
          "status": {
            "type": "string"
          },
          "total_plans": {
            "type": "integer"
          },
          "truncated": {
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 46. inspect_05-resolve_targets

**CoS · beyond**

```txt
Plan에 등록된 Scene·Holon 대상과 저장된 Holon 정보 조회. Step 지정 시 해당 Plan 소속을 검사하며 대상은 Plan 기준. Scene 전체로 Holon을 늘리거나 Rhino의 현재 구성원을 확인하지 않는다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "type": "string"
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "type": "string"
    }
  },
  "required": [
    "plan_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holon_ids": {
            "items": {},
            "type": "array"
          },
          "holons": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "live_verified": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "plan_id": {
            "type": "string"
          },
          "revision": {
            "description": "변경을 검사할 때 현재 loop_no와 함께 사용",
            "type": "integer"
          },
          "scene_ids": {
            "items": {},
            "type": "array"
          },
          "source": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "step_id": {}
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 47. intersect_01-find

**CoS · beyond**

```txt
닫힌 솔리드 중 양의 부피가 겹치는 객체 쌍을 집계. 전체 검사가 끝나야 건수를 반환한다. 0건은 검사 범위의 결과이며 간격이나 전체 설계 적합성은 별개. 계산할 수 없는 객체·쌍이나 페이지 오류는 미판정(assessment=incomplete)이다. 확인된 대상·이유와 해당 페이지의 모델 공차·단위를 반환하며 null은 확인 불가를 뜻한다. 면 접촉만으로도 계산이 불완전할 수 있다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_block": {
      "default": false,
      "description": "중첩 블록의 배치 변환을 적용해 구성원까지 검사. false이면 블록 제외.",
      "type": "boolean"
    },
    "object_ids": {
      "description": "서로 다른 현재 최상위 Rhino 객체 GUID 1..512개. 내부에서 페이지를 나누며 전체를 하나의 범위로 검사.",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "object_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_block": {
      "default": false,
      "description": "중첩 블록의 배치 변환을 적용해 구성원까지 검사. false이면 블록 제외.",
      "type": "boolean"
    },
    "object_ids": {
      "description": "서로 다른 현재 최상위 Rhino 객체 GUID 1..512개. 내부에서 페이지를 나누며 전체를 하나의 범위로 검사.",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "object_ids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assessment": {
            "const": "incomplete",
            "description": "미판정. 전체 범위의 겹침 건수 미확정."
          },
          "document_units": {
            "description": "해당 검사에서 확인한 문서 길이 단위. null은 확인 불가.",
            "type": [
              "string",
              "null"
            ]
          },
          "error_code": {
            "type": "string"
          },
          "failed_pairs": {
            "description": "계산을 마치지 못한 쌍과 사유. null은 확인 불가.",
            "items": {
              "type": "object"
            },
            "type": [
              "array",
              "null"
            ]
          },
          "intersections": {
            "properties": {
              "number": {
                "description": "양의 부피가 겹치는 객체 쌍의 수",
                "type": "integer"
              }
            },
            "type": "object"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "tolerance_model_units": {
            "description": "미판정이 발생한 검사에서 확인한 모델 길이 공차. null은 확인 불가.",
            "type": [
              "number",
              "null"
            ]
          },
          "unsupported_objects": {
            "description": "검사할 수 없는 것으로 확인된 객체와 사유. null은 확인 불가.",
            "items": {
              "type": "object"
            },
            "type": [
              "array",
              "null"
            ]
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 48. intersect_02-resolve

**CoS · beyond**

```txt
겹친 객체 쌍을 캡처해 비교하고 지정한 객체에서 겹친 부분을 제거. 검토 시 실제 카메라와 선택이 바뀐다. 완료 후에도 건너뛴 쌍은 남는다. 다음 쌍의 검사 미판정(assessment=incomplete)에는 대상·이유와 해당 검사에서 확인한 모델 공차·단위를 반환하며 null은 확인 불가를 뜻한다. 직전 수정이 이미 적용됐을 수 있으므로 previous_result와 실제 형상을 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "choice": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "const": "skip",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1 또는 2: 해당 번호 객체에서 겹친 부분 제거. skip: 두 객체 유지. 선택 제출 시 review_id를 지정하고 object_ids는 생략. 검토만 하거나 이어갈 때는 choice 생략."
    },
    "include_block": {
      "default": false,
      "description": "새 검토에 배치 변환을 적용한 중첩 블록 구성원 포함. 블록 정의 편집은 지원하지 않음.",
      "type": "boolean"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 검토를 시작할 현재 최상위 객체의 서로 다른 GUID 1..512개. 이어서 검토하거나 선택을 제출할 때는 생략."
    },
    "review_id": {
      "default": "",
      "description": "비교 화면의 대상을 식별하는 반환 ID. choice 제출 시 필수. 완료됐거나 새 검토로 대체된 ID는 재사용 불가.",
      "type": "string"
    },
    "user_text": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 검토 범위의 객체 속성 User Text 조건 배열. 예: [{\"key\":\"floor\",\"any_of\":[\"2F\"]}]. 한 객체가 모든 조건과 일치하는 쌍을 표시. 양쪽 값은 objects[].attributes.user_strings.values에서 확인. 중첩 블록에는 정의 구성원의 속성 적용."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "choice": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "const": "skip",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1 또는 2: 해당 번호 객체에서 겹친 부분 제거. skip: 두 객체 유지. 선택 제출 시 review_id를 지정하고 object_ids는 생략. 검토만 하거나 이어갈 때는 choice 생략."
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_block": {
      "default": false,
      "description": "새 검토에 배치 변환을 적용한 중첩 블록 구성원 포함. 블록 정의 편집은 지원하지 않음.",
      "type": "boolean"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 검토를 시작할 현재 최상위 객체의 서로 다른 GUID 1..512개. 이어서 검토하거나 선택을 제출할 때는 생략."
    },
    "review_id": {
      "default": "",
      "description": "비교 화면의 대상을 식별하는 반환 ID. choice 제출 시 필수. 완료됐거나 새 검토로 대체된 ID는 재사용 불가.",
      "type": "string"
    },
    "user_text": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 검토 범위의 객체 속성 User Text 조건 배열. 예: [{\"key\":\"floor\",\"any_of\":[\"2F\"]}]. 한 객체가 모든 조건과 일치하는 쌍을 표시. 양쪽 값은 objects[].attributes.user_strings.values에서 확인. 중첩 블록에는 정의 구성원의 속성 적용."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "assessment": {
      "const": "incomplete",
      "description": "미판정. 전체 범위의 겹침 건수 미확정."
    },
    "document_units": {
      "description": "해당 검사에서 확인한 문서 길이 단위. null은 확인 불가.",
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "failed_pairs": {
      "description": "계산을 마치지 못한 쌍과 사유. null은 확인 불가.",
      "items": {
        "type": "object"
      },
      "type": [
        "array",
        "null"
      ]
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "objects": {
      "description": "choice에서 사용할 번호가 붙은 검토 쌍의 구성원",
      "items": {
        "properties": {
          "attributes": {
            "properties": {
              "user_strings": {
                "description": "Rhino 객체 속성의 User Text",
                "properties": {
                  "total_keys": {
                    "description": "응답 제한을 적용하기 전 저장된 키 수",
                    "type": "integer"
                  },
                  "truncated": {
                    "type": "boolean"
                  },
                  "values": {
                    "description": "저장된 문자열이나 응답 제한으로 생략된 값의 표시",
                    "type": "object"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          },
          "user_dictionary": {
            "description": "객체 속성과 형상의 UserDictionary를 구분",
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "skipped_pairs": {
      "type": "number"
    },
    "state": {
      "description": "awaiting_choice이면 비교 결과를 보고 choice를 제출",
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "tolerance_model_units": {
      "description": "미판정이 발생한 검사에서 확인한 모델 길이 공차. null은 확인 불가.",
      "type": [
        "number",
        "null"
      ]
    },
    "unsupported_objects": {
      "description": "검사할 수 없는 것으로 확인된 객체와 사유. null은 확인 불가.",
      "items": {
        "type": "object"
      },
      "type": [
        "array",
        "null"
      ]
    }
  },
  "type": "object"
}
```

</details>


### 49. model_01-assign_material

**CoS · beyond**

```txt
Rhino 객체에 라이브러리 렌더 재료와 선택적 구축 메타데이터 지정. 재료는 객체에 직접 지정하고 레이어는 유지. 중복 GUID는 한 번만 처리. 메타데이터는 inspect_02-get_objects tool에서 fields=["user_text"]로 읽거나 filters.user_text로 검색.

success는 전체 처리, partial은 일부 처리. executed는 적용한 객체가 없거나 적용 결과를 읽지 못한 상태. 결과 확인이 안 된 경우 재시도 전에 Rhino에서 대상 객체 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "apply_render_material": {
      "default": true,
      "type": "boolean"
    },
    "attach_metadata": {
      "default": false,
      "description": "Almond 재료·구축 메타데이터를 객체 속성에 기록",
      "type": "boolean"
    },
    "construction_detail": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 구축 상세",
      "type": "string"
    },
    "construction_reference": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "{\"kind\":\"construction_system\",\"id\":\"확인한 system_id\"} 형식. attach_metadata=true일 때 기록하며 construction_system을 함께 지정하면 동일한 시스템 필요."
    },
    "construction_system": {
      "default": "",
      "description": "라이브러리에서 확인한 구축 시스템 ID. attach_metadata=true일 때 기록하며 construction_reference와 함께 지정하면 동일한 시스템 필요.",
      "type": "string"
    },
    "floor": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 층 레이블",
      "type": "string"
    },
    "guids": {
      "description": "현재 Rhino 객체의 GUID. 관찰 또는 생성 결과에서 가져온 값.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "material_id": {
      "description": "model_04-list_materials tool에서 include_ids=true로 조회한 표준 재료 ID",
      "type": "string"
    },
    "structural_role": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 구조 역할",
      "type": "string"
    }
  },
  "required": [
    "guids",
    "material_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "apply_render_material": {
      "default": true,
      "type": "boolean"
    },
    "attach_metadata": {
      "default": false,
      "description": "Almond 재료·구축 메타데이터를 객체 속성에 기록",
      "type": "boolean"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "construction_detail": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 구축 상세",
      "type": "string"
    },
    "construction_reference": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "{\"kind\":\"construction_system\",\"id\":\"확인한 system_id\"} 형식. attach_metadata=true일 때 기록하며 construction_system을 함께 지정하면 동일한 시스템 필요."
    },
    "construction_system": {
      "default": "",
      "description": "라이브러리에서 확인한 구축 시스템 ID. attach_metadata=true일 때 기록하며 construction_reference와 함께 지정하면 동일한 시스템 필요.",
      "type": "string"
    },
    "floor": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 층 레이블",
      "type": "string"
    },
    "guids": {
      "description": "현재 Rhino 객체의 GUID. 관찰 또는 생성 결과에서 가져온 값.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "material_id": {
      "description": "model_04-list_materials tool에서 include_ids=true로 조회한 표준 재료 ID",
      "type": "string"
    },
    "structural_role": {
      "default": "",
      "description": "attach_metadata=true일 때 기록할 구조 역할",
      "type": "string"
    }
  },
  "required": [
    "guids",
    "material_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "applied_count": {
            "description": "처리 성공 수. 실제로 달라진 객체 수는 changed_count 참조.",
            "type": "integer"
          },
          "applied_guids": {
            "description": "처리 성공 GUID. 실제 변경이 확인된 객체는 changed_guids 참조.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "layer_path": {
            "type": [
              "string",
              "null"
            ]
          },
          "material_id": {
            "type": "string"
          },
          "material_metadata_attached": {
            "description": "attach_metadata와 apply_render_material을 모두 요청했는지 표시",
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "metadata_attached": {
            "description": "attach_metadata와 함께 렌더 재료 적용 또는 추가 구축 메타데이터를 지정했는지 표시",
            "type": "boolean"
          },
          "next_step_guide": {
            "type": "string"
          },
          "render_material_applied": {
            "description": "렌더 재료 적용을 요청했는지 표시. 변경 확인은 changed_guids 참조.",
            "type": "boolean"
          },
          "requested_count": {
            "type": "integer"
          },
          "result_error": {
            "type": "string"
          },
          "rhino_material_name": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "ue_material_slot": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 50. model_02-edit_planar_face

**CoS · beyond**

```txt
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 가져온다. 일부 오류 응답에는 mutation_state가 없을 수 있다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_geometry_crc": {
      "description": "면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.",
      "type": "integer"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "face_index": {
      "description": "같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.",
      "type": "integer"
    },
    "object_id": {
      "description": "연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID",
      "type": "string"
    },
    "translation": {
      "description": "문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.",
      "items": {
        "anyOf": [
          {
            "type": "number"
          },
          {
            "type": "integer"
          }
        ]
      },
      "type": "array"
    }
  },
  "required": [
    "object_id",
    "face_index",
    "expected_geometry_crc",
    "translation"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_geometry_crc": {
      "description": "면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.",
      "type": "integer"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "face_index": {
      "description": "같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.",
      "type": "integer"
    },
    "object_id": {
      "description": "연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID",
      "type": "string"
    },
    "translation": {
      "description": "문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.",
      "items": {
        "anyOf": [
          {
            "type": "number"
          },
          {
            "type": "integer"
          }
        ]
      },
      "type": "array"
    }
  },
  "required": [
    "object_id",
    "face_index",
    "expected_geometry_crc",
    "translation",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "result": {
            "properties": {
              "edited": {
                "description": "대상 객체와 기존 CRC를 확인한 뒤 편집을 적용한 결과",
                "type": "boolean"
              },
              "geometry_crc": {
                "description": "추가 면 편집 전 faces와 새 CRC를 다시 조회. 편집 후 면 인덱스가 달라질 수 있다.",
                "type": "number"
              },
              "object_id": {
                "type": "string"
              },
              "previous_geometry_crc": {
                "type": "number"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 51. model_03-edit_planar_faces

**CoS · beyond**

```txt
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 객체별 면 번호와 CRC는 같은 관찰에서 가져온다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않는다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "edits": {
      "description": "서로 다른 Brep에 대한 항목 1..32개. 각 항목에 object_id, face_index, expected_geometry_crc, translation을 지정하며 model_02-edit_planar_face tool과 동일한 조건 적용.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    }
  },
  "required": [
    "edits"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "edits": {
      "description": "서로 다른 Brep에 대한 항목 1..32개. 각 항목에 object_id, face_index, expected_geometry_crc, translation을 지정하며 model_02-edit_planar_face tool과 동일한 조건 적용.",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    }
  },
  "required": [
    "edits",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "result": {
            "description": "객체 교체 중 실패하면 일부 편집이 남을 수 있다.",
            "properties": {
              "applied_count": {
                "type": "integer"
              },
              "complete": {
                "description": "모든 항목의 적용을 확인했을 때 true",
                "type": "boolean"
              },
              "items": {
                "description": "입력 순서의 항목별 결과. 실패 단계와 메시지 포함.",
                "items": {
                  "properties": {
                    "edited": {
                      "type": "boolean"
                    },
                    "geometry_crc": {
                      "description": "다음 면 편집 전 면 인덱스와 CRC를 다시 조회",
                      "type": "number"
                    },
                    "previous_geometry_crc": {
                      "type": "number"
                    },
                    "status": {
                      "description": "applied, rejected, failed, unknown, not_attempted",
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "mutation_state": {
                "description": "not_started, applied, partial, unknown 등. partial 또는 unknown이면 전체 배치를 자동 재실행하지 않음.",
                "type": "string"
              },
              "requested_count": {
                "type": "integer"
              },
              "status": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 52. model_04-list_materials

**CoS · beyond**

```txt
라이브러리에서 이름·설명·태그나 분류로 재료 검색. model_01-assign_material tool에 사용할 material_id는 include_ids=true로 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "query": {
      "default": "",
      "description": "이름·설명·태그 검색. 대소문자 구분 없음.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "query": {
      "default": "",
      "description": "이름·설명·태그 검색. 대소문자 구분 없음.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "materials": {
            "items": {
              "properties": {
                "category": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 53. model_05-setup

**CoS · beyond**

```txt
연결된 Rhino 문서에 표준 재료를 등록하고 M 아래 분류·시스템·부재 역할별 레이어와 색·재료를 설정.

overwrite=false는 누락 항목만 생성하고 기존 속성의 차이를 보고. true는 누락 항목을 생성하고 기존 항목의 사전 정의 속성도 갱신. applied=true는 차이와 오류가 없는 상태. incomplete여도 일부 항목이 이미 생성·변경됐을 수 있다.

객체별 재료는 model_04-list_materials tool로 찾고 model_01-assign_material tool로 지정.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "overwrite": {
      "type": "boolean"
    }
  },
  "required": [
    "overwrite"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "overwrite": {
      "type": "boolean"
    }
  },
  "required": [
    "overwrite",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "applied": {
            "type": "boolean"
          },
          "changes": {
            "description": "재료 레시피별 RenderMaterial과 지정 레이어의 처리 내역. 레이어 재료 지정으로 추가된 Rhino Materials 테이블 항목은 집계에서 제외. 변경 내역을 지원하는 Bridge에서 제공.",
            "items": {
              "properties": {
                "action": {
                  "description": "created: RenderMaterial 수 증가 또는 레이어 생성. updated: 기존 값 변경. preserved: 기존 값 유지. unchanged: 작성 후 관측값 동일. unconfirmed: 작성 후 확인 실패. skipped: 작성 전 중단.",
                  "enum": [
                    "created",
                    "updated",
                    "preserved",
                    "unchanged",
                    "unconfirmed",
                    "skipped"
                  ],
                  "type": "string"
                },
                "current_count": {
                  "description": "처리 후 일치하는 RenderMaterial 수 또는 지정 레이어의 존재 여부(0/1)",
                  "type": [
                    "integer",
                    "null"
                  ]
                },
                "kind": {
                  "description": "material: RenderMaterial을 확인한 재료 레시피. layer: 지정 레이어.",
                  "enum": [
                    "material",
                    "layer"
                  ],
                  "type": "string"
                },
                "name": {
                  "description": "재료 레시피 이름 또는 레이어 전체 경로",
                  "type": "string"
                },
                "previous_count": {
                  "description": "처리 전 일치하는 RenderMaterial 수 또는 지정 레이어의 존재 여부(0/1)",
                  "type": [
                    "integer",
                    "null"
                  ]
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "differences": {
            "description": "설정 기준과 최종 관측값이 다른 항목",
            "items": {
              "properties": {
                "current": {},
                "expected": {},
                "kind": {
                  "type": "string"
                },
                "name": {
                  "description": "재료 이름 또는 레이어 경로",
                  "type": "string"
                },
                "property": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "errors": {
            "items": {
              "properties": {
                "kind": {
                  "type": "string"
                },
                "message": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 54. plan_02-create

**CoS · beyond**

```txt
Phase 또는 Plan 생성. Plan은 `scope`의 Step 템플릿을 적용해 `loop_no=0`, `revision=1`에서 시작하며 실제 작업은 별도 수행. 생성 오류는 `result.status`에서 확인. 자동 생성된 Step은 plan_05-get tool로 확인.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "description": {
              "default": "",
              "type": "string"
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                }
              ],
              "default": "",
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명."
            },
            "name": {
              "description": "공백만 있는 이름은 거부.",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "status": {
              "default": "pending",
              "enum": [
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "name"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "하위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "결과나 결정에 의존하는 관련 Plan. 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "goal": {
              "description": "공백만 있는 목표는 거부.",
              "type": "string"
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "phase_id": {
              "default": "",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "scene_id": {
              "default": "",
              "description": "단일 Scene용 호환 입력. `scene_ids`와 함께 지정하면 배열의 첫 ID와 일치해야 함.",
              "type": "string"
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략하거나 `null`이면 `scene_id` 사용."
            },
            "scope": {
              "default": "house",
              "description": "Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능.",
              "type": "string"
            },
            "target": {
              "const": "plan",
              "type": "string"
            },
            "title": {
              "description": "공백만 있는 제목은 거부.",
              "type": "string"
            }
          },
          "required": [
            "target",
            "title",
            "goal"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "description": {
              "default": "",
              "type": "string"
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                }
              ],
              "default": "",
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명."
            },
            "name": {
              "description": "공백만 있는 이름은 거부.",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "status": {
              "default": "pending",
              "enum": [
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "name"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "하위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "결과나 결정에 의존하는 관련 Plan. 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "goal": {
              "description": "공백만 있는 목표는 거부.",
              "type": "string"
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "phase_id": {
              "default": "",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "scene_id": {
              "default": "",
              "description": "단일 Scene용 호환 입력. `scene_ids`와 함께 지정하면 배열의 첫 ID와 일치해야 함.",
              "type": "string"
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략하거나 `null`이면 `scene_id` 사용."
            },
            "scope": {
              "default": "house",
              "description": "Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능.",
              "type": "string"
            },
            "target": {
              "const": "plan",
              "type": "string"
            },
            "title": {
              "description": "공백만 있는 제목은 거부.",
              "type": "string"
            }
          },
          "required": [
            "target",
            "title",
            "goal"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "phase": {
            "properties": {
              "phase_id": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "plan": {
            "properties": {
              "loop_no": {
                "type": "integer"
              },
              "plan_id": {
                "type": "string"
              },
              "revision": {
                "description": "수정 시 `loop_no`와 함께 `expected_revision`으로 사용 가능.",
                "type": "integer"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 55. plan_03-execute_looping

**CoS · beyond**

```txt
Plan의 새 작업 회차 시작 또는 최신 회차 재개. Step 실행은 에이전트가 직접 수행.

새 회차의 Step은 `pending`에서 시작하며 이전 회차 기록은 `previous_loop`에서 확인. 실행된 회차가 있어야 `resume=true`로 재개 가능.

다음 회차를 시작하기 전, 현재 Plan Goal을 사용자의 피드백 및 작업방향에 맞게 align하여 수정하고, 다음 회차에 필요하지 않음이 분명한 라이노 객체, layout, namedview, layer등을 삭제한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "default": "",
      "description": "최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.",
      "type": "string"
    },
    "feedback": {
      "default": "",
      "description": "재개 시 생략하거나 비우면 이전 피드백 유지.",
      "type": "string"
    },
    "plan_id": {
      "description": "plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.",
      "type": "string"
    },
    "resume": {
      "default": false,
      "description": "`true`면 최신 회차 재개, `false`면 새 회차 시작.",
      "type": "boolean"
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "default": "",
      "description": "최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "feedback": {
      "default": "",
      "description": "재개 시 생략하거나 비우면 이전 피드백 유지.",
      "type": "string"
    },
    "plan_id": {
      "description": "plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.",
      "type": "string"
    },
    "resume": {
      "default": false,
      "description": "`true`면 최신 회차 재개, `false`면 새 회차 시작.",
      "type": "boolean"
    }
  },
  "required": [
    "plan_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "feedback": {
      "type": "string"
    },
    "goal": {
      "type": "string"
    },
    "loop_no": {
      "type": "integer"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "next_step_id": {
      "description": "다음 작업으로 선택할 첫 미완료 Step.",
      "type": [
        "string",
        "null"
      ]
    },
    "plan_artifact_dir": {
      "type": "string"
    },
    "plan_id": {
      "type": "string"
    },
    "plan_status": {
      "description": "회차를 시작해도 Plan 상태는 유지.",
      "type": "string"
    },
    "policy_reminder": {
      "type": "string"
    },
    "previous_loop": {
      "description": "첫 회차에는 실행 전 0번 기록을 포함할 수 있음.",
      "properties": {
        "loop_no": {
          "type": "integer"
        },
        "steps": {
          "items": {
            "properties": {
              "depends_on": {
                "description": "선행 Step UUID.",
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "design_rationale": {
                "type": "string"
              },
              "input_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "kind": {
                "type": "string"
              },
              "loop_no": {
                "type": "integer"
              },
              "name": {
                "type": "string"
              },
              "output_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "position": {
                "type": "integer"
              },
              "status": {
                "description": "Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.",
                "type": "string"
              },
              "step_id": {
                "description": "회차가 바뀌어도 유지되는 Step UUID.",
                "type": "string"
              },
              "step_type": {
                "type": "string"
              },
              "takeaways": {
                "description": "다음 작업에 넘길 주요 발견과 교훈.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": [
        "object",
        "null"
      ]
    },
    "revision": {
      "type": "integer"
    },
    "status": {
      "type": "string"
    },
    "step_id": {
      "type": "string"
    },
    "steps": {
      "items": {
        "properties": {
          "depends_on": {
            "description": "선행 Step UUID.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "design_rationale": {
            "type": "string"
          },
          "input_refs": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "kind": {
            "type": "string"
          },
          "loop_no": {
            "type": "integer"
          },
          "name": {
            "type": "string"
          },
          "output_refs": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "position": {
            "type": "integer"
          },
          "status": {
            "description": "Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.",
            "type": "string"
          },
          "step_id": {
            "description": "회차가 바뀌어도 유지되는 Step UUID.",
            "type": "string"
          },
          "step_type": {
            "type": "string"
          },
          "takeaways": {
            "description": "다음 작업에 넘길 주요 발견과 교훈.",
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "title": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 56. plan_05-get

**CoS · beyond**

```txt
Phase·Plan·Step 작업 기록 조회. `include_details=true`로 상세를 포함. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로로 열어 확인.

Plan·Step 조회에 `revision`을 지정하면 현재 번호여도 읽기 전용 스냅샷 반환.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "phase_id": {
              "type": "string"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태."
            },
            "target": {
              "const": "plan",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태."
            },
            "step_id": {
              "description": "같은 요청의 `plan_id`에 속한 Step만 조회 가능.",
              "type": "string"
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "phase_id": {
              "type": "string"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태."
            },
            "target": {
              "const": "plan",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
              "default": false,
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태."
            },
            "step_id": {
              "description": "같은 요청의 `plan_id`에 속한 Step만 조회 가능.",
              "type": "string"
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "id": {
            "type": "string"
          },
          "loop_no": {
            "description": "0은 회차 시작 전 기록.",
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "phase": {
            "properties": {
              "depends_on": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "description": {
                "type": "string"
              },
              "file_name": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "plan_titles": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "previous_id": {
                "type": [
                  "string",
                  "null"
                ]
              }
            },
            "type": "object"
          },
          "plan": {
            "properties": {
              "artifact_dir": {
                "description": "회차별 산출물 폴더를 담는 Plan 루트.",
                "type": "string"
              },
              "artifact_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "child_plan": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "created_at": {
                "description": "한국 시간 `YYYY-MM-DD-HH:MM`.",
                "type": "string"
              },
              "depends_on": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "feedback": {
                "type": "string"
              },
              "goal": {
                "type": "string"
              },
              "holon_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "loop_artifact_dir": {
                "type": "string"
              },
              "parent_plan": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "phase": {
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "phase_id": {
                    "type": "string"
                  }
                },
                "type": [
                  "object",
                  "null"
                ]
              },
              "previous_id": {
                "type": [
                  "string",
                  "null"
                ]
              },
              "scene_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "scope": {
                "description": "Step 템플릿 키.",
                "type": "string"
              },
              "steps": {
                "items": {
                  "properties": {
                    "loop_no": {
                      "type": "integer"
                    },
                    "name": {
                      "type": "string"
                    },
                    "status": {
                      "type": "string"
                    },
                    "step_id": {
                      "type": "string"
                    },
                    "step_type": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "updated_at": {
                "description": "한국 시간 `YYYY-MM-DD-HH:MM`.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "plan_id": {
            "type": "string"
          },
          "read_only": {
            "description": "과거 회차 또는 명시적으로 지정한 리비전이면 `true`. 수정 전 최신 기록 재조회.",
            "type": "boolean"
          },
          "revision": {
            "type": "integer"
          },
          "status": {
            "description": "성공 시 `pending`, `running`, `paused`, `completed`, `failed`, `blocked` 중 하나. 조회 실패는 `error`.",
            "type": "string"
          },
          "step": {
            "properties": {
              "design_rationale": {
                "type": "string"
              },
              "input_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "output_refs": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "step_type": {
                "type": "string"
              },
              "takeaways": {
                "description": "다음 작업에 넘길 주요 발견과 교훈.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "type": {
            "enum": [
              "phase",
              "plan",
              "step"
            ],
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 57. plan_07-list_revisions

**CoS · beyond**

```txt
Plan 리비전 목록을 최신 회차·리비전 순으로 조회. Step 필터는 해당 Step의 직접 변경만 포함. `offset` 미지원.

과거 기록은 plan_05-get tool에 같은 `loop_no`와 `revision`을 넣어 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환."
    },
    "limit": {
      "default": 50,
      "description": "1~500.",
      "type": "integer"
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략·`null`은 모든 회차, 0은 실행 전 기록."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "description": "생략하거나 비우면 Step으로 필터링하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환."
    },
    "limit": {
      "default": 50,
      "description": "1~500.",
      "type": "integer"
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략·`null`은 모든 회차, 0은 실행 전 기록."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "description": "생략하거나 비우면 Step으로 필터링하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "plan_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "plan_id": {
            "description": "행의 `loop_no`·`revision`과 함께 plan_05-get tool의 `request`에 사용.",
            "type": "string"
          },
          "revisions": {
            "items": {
              "properties": {
                "created_at": {
                  "description": "`audit` 또는 `all` 그룹에서 반환.",
                  "type": "string"
                },
                "loop_no": {
                  "type": "integer"
                },
                "operation": {
                  "type": "string"
                },
                "revision": {
                  "type": "integer"
                },
                "step_id": {
                  "type": [
                    "string",
                    "null"
                  ]
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "status": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 58. plan_08-list

**CoS · beyond**

```txt
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록 조회. `offset` 미지원. Step 목록과 리비전 정보는 같은 스냅샷을 기준으로 반환.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "field_groups": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "`description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환."
            },
            "limit": {
              "default": 50,
              "description": "1~500.",
              "type": "integer"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "limit": {
              "default": 50,
              "description": "1~500.",
              "type": "integer"
            },
            "phase_id": {
              "default": "",
              "description": "생략하거나 비우면 Phase 소속 여부와 관계없이 조회.",
              "type": "string"
            },
            "scene_id": {
              "default": "",
              "description": "생략하거나 비우면 Scene 연결 여부와 관계없이 조회.",
              "type": "string"
            },
            "status": {
              "default": "",
              "description": "생략하거나 비우면 상태 필터를 적용하지 않음.",
              "enum": [
                "",
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "target": {
              "const": "plan",
              "type": "string"
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "limit": {
              "default": 50,
              "description": "1~500. 정의된 순서의 앞부분을 반환.",
              "maximum": 500,
              "minimum": 1,
              "type": "integer"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태. 지정하면 읽기 전용 스냅샷."
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "field_groups": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "`description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환."
            },
            "limit": {
              "default": 50,
              "description": "1~500.",
              "type": "integer"
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "limit": {
              "default": 50,
              "description": "1~500.",
              "type": "integer"
            },
            "phase_id": {
              "default": "",
              "description": "생략하거나 비우면 Phase 소속 여부와 관계없이 조회.",
              "type": "string"
            },
            "scene_id": {
              "default": "",
              "description": "생략하거나 비우면 Scene 연결 여부와 관계없이 조회.",
              "type": "string"
            },
            "status": {
              "default": "",
              "description": "생략하거나 비우면 상태 필터를 적용하지 않음.",
              "enum": [
                "",
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "target": {
              "const": "plan",
              "type": "string"
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "limit": {
              "default": 50,
              "description": "1~500. 정의된 순서의 앞부분을 반환.",
              "maximum": 500,
              "minimum": 1,
              "type": "integer"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록."
            },
            "plan_id": {
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "생략·`null`은 선택한 회차의 최신 상태. 지정하면 읽기 전용 스냅샷."
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "loop_no": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "phases": {
            "items": {
              "properties": {
                "depends_on": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "file_name": {
                  "description": "`scope` 또는 `all` 그룹에서 반환하는 Rhino 파일명.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "name": {
                  "type": "string"
                },
                "phase_id": {
                  "type": "string"
                },
                "plan_count": {
                  "type": "integer"
                },
                "previous_id": {
                  "type": [
                    "string",
                    "null"
                  ]
                },
                "status": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "plan_id": {
            "type": "string"
          },
          "plans": {
            "items": {
              "properties": {
                "loop_no": {
                  "type": "integer"
                },
                "plan_id": {
                  "type": "string"
                },
                "revision": {
                  "type": "integer"
                },
                "scope": {
                  "description": "Step 템플릿 키.",
                  "type": "string"
                },
                "status": {
                  "type": "string"
                },
                "title": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "read_only": {
            "description": "과거 회차 또는 명시적으로 지정한 리비전이면 `true`.",
            "type": "boolean"
          },
          "revision": {
            "type": "integer"
          },
          "status": {
            "type": "string"
          },
          "steps": {
            "items": {
              "properties": {
                "loop_no": {
                  "type": "integer"
                },
                "name": {
                  "type": "string"
                },
                "status": {
                  "type": "string"
                },
                "step_id": {
                  "description": "회차가 바뀌어도 유지되는 Step UUID.",
                  "type": "string"
                },
                "step_type": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 59. plan_09-rename_artifact_folder

**CoS · beyond**

```txt
Plan 산출물 폴더 이름 변경 및 저장된 Plan·Step 경로 참조 갱신. 먼저 plan_10-set_working tool로 산출물 폴더를 지정.

Loop를 이미 실행했거나 다른 Plan의 과거 회차가 참조하는 폴더는 변경 불가. 같은 이름은 변경 없이 성공. 대상이 이미 존재하거나 다른 Plan 소유이면 실패. 실제 변경 시 새 리비전을 저장하고 이전 리비전은 보존.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "description": "경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.",
      "type": "string"
    },
    "plan_id": {
      "default": "",
      "description": "생략하거나 비우면 현재 선택된 Plan 사용.",
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "name": {
      "description": "경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.",
      "type": "string"
    },
    "plan_id": {
      "default": "",
      "description": "생략하거나 비우면 현재 선택된 Plan 사용.",
      "type": "string"
    }
  },
  "required": [
    "name",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "previous_artifact_dir": {
      "description": "폴더 이름이 실제로 변경된 경우에만 반환.",
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 60. plan_10-set_working

**CoS · beyond**

```txt
현재 연결의 산출물 작업 대상으로 Plan과 선택적인 Step 지정. 작업 실행과 Plan·Step 상태 변경은 별도.

최초 선택에서 산출물 경로를 정하면 리비전이 증가할 수 있음. 이후 같은 경로 재사용. `artifact_dir`은 Loop 시작 전 Plan 루트, 시작 후 현재 회차 폴더.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "default": "",
      "description": "최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.",
      "type": "string"
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략·`null`은 현재 회차. 이전 회차 또는 존재하지 않는 회차는 선택 불가."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "description": "생략하면 Plan만 선택.",
      "type": "string"
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "default": "",
      "description": "최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "생략·`null`은 현재 회차. 이전 회차 또는 존재하지 않는 회차는 선택 불가."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
      "type": "string"
    },
    "step_id": {
      "default": "",
      "description": "생략하면 Plan만 선택.",
      "type": "string"
    }
  },
  "required": [
    "plan_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "description": "script_01-run_project_python tool의 작업 디렉터리.",
      "type": [
        "string",
        "null"
      ]
    },
    "error_code": {
      "type": "string"
    },
    "loop_no": {
      "type": "integer"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "plan_artifact_dir": {
      "type": "string"
    },
    "plan_id": {
      "type": "string"
    },
    "revision": {
      "type": "integer"
    },
    "status": {
      "type": "string"
    },
    "step_id": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 61. plan_12-update

**CoS · beyond**

```txt
Phase·Plan 작업 정보 또는 Step 상태·입출력 참조·판단 기록 수정. Plan·Step은 현재 회차만 수정 가능.

`depends_on`, `input_refs`, `output_refs`는 `add`/`remove` 패치. 나머지 대상·산출물·상하위 관계 배열은 전체 교체. 생략·`null`은 기존 값 유지, 교체 배열의 `[]`는 전체 삭제.

응답 `status`는 모두 반영해 값이 바뀌면 `updated`, 바뀐 값이 없으면 `no_change`, 변경과 건너뛴 항목이 함께 있으면 `partial_success`. 건너뛴 항목은 `issues`에서 확인. Step을 `completed`로 지정하면 함께 전달한 필드와 한 번에 저장.

Plan 완료는 사용자 확인 후 지정.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음."
            },
            "description": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 설명 삭제."
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명. 빈 문자열 또는 `[]`는 연결 해제, 생략·`null`은 연결 유지."
            },
            "name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 이름은 거부."
            },
            "phase_id": {
              "description": "plan_08-list tool의 `request.target=\"phase\"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 Phase `id`.",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 연결 해제."
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "artifact_refs": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "결과나 결정에 의존하는 관련 Plan. Plan ID 형식만 검사. 대상 존재·자기 참조·순환은 확인하지 않으며 순서나 완료도 강제하지 않음."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "goal": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 목표는 거부."
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "phase_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 Phase 소속 해제."
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "작업 순서상 직전 Plan. 빈 문자열은 연결 해제."
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "`completed`는 사용자의 완료 결정 후 지정."
            },
            "target": {
              "const": "plan",
              "type": "string"
            },
            "title": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 제목은 거부."
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "design_rationale": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "설계 결정의 이유와 근거. 빈 문자열은 내용 삭제."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "input_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "output_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
              "type": "string"
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "step_id": {
              "description": "plan_05-get tool의 Plan 상세에서 확인한 Step ID.",
              "type": "string"
            },
            "takeaways": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "다음 작업에 넘길 핵심 결론과 확인 사항. 빈 문자열은 내용 삭제."
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음."
            },
            "description": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 설명 삭제."
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명. 빈 문자열 또는 `[]`는 연결 해제, 생략·`null`은 연결 유지."
            },
            "name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 이름은 거부."
            },
            "phase_id": {
              "description": "plan_08-list tool의 `request.target=\"phase\"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 Phase `id`.",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 연결 해제."
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "target": {
              "const": "phase",
              "type": "string"
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "artifact_refs": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "결과나 결정에 의존하는 관련 Plan. Plan ID 형식만 검사. 대상 존재·자기 참조·순환은 확인하지 않으며 순서나 완료도 강제하지 않음."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "goal": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 목표는 거부."
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "phase_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 문자열은 Phase 소속 해제."
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
              "type": "string"
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "작업 순서상 직전 Plan. 빈 문자열은 연결 해제."
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "`completed`는 사용자의 완료 결정 후 지정."
            },
            "target": {
              "const": "plan",
              "type": "string"
            },
            "title": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "빈 제목은 거부."
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "design_rationale": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "설계 결정의 이유와 근거. 빈 문자열은 내용 삭제."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "input_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "output_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id",
              "type": "string"
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null
            },
            "step_id": {
              "description": "plan_05-get tool의 Plan 상세에서 확인한 Step ID.",
              "type": "string"
            },
            "takeaways": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "다음 작업에 넘길 핵심 결론과 확인 사항. 빈 문자열은 내용 삭제."
            },
            "target": {
              "const": "step",
              "type": "string"
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "request",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "changed": {
            "description": "실제 저장 값이 바뀌었으면 true. Step 완료 후 Rhino 후속 작업이 실패해도 저장된 변경은 유지.",
            "type": "boolean"
          },
          "cleanup_state": {
            "description": "실패 시 확인된 Rhino 후속 작업 상태.",
            "enum": [
              "not_started",
              "rolled_back",
              "unknown"
            ]
          },
          "error_code": {
            "type": "string"
          },
          "issues": {
            "description": "이 목록에 없는 변경은 저장되었을 수 있음.",
            "items": {
              "properties": {
                "field": {
                  "type": "string"
                },
                "index": {
                  "description": "해당 패치 배열에서의 0 기반 위치.",
                  "type": "integer"
                },
                "operation": {
                  "description": "`add` 또는 `remove`.",
                  "type": "string"
                },
                "reason": {
                  "type": "string"
                },
                "value": {}
              },
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "phase": {
            "properties": {
              "phase_id": {
                "type": "string"
              },
              "status": {
                "description": "업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "plan": {
            "description": "Step 수정 응답에도 소속 Plan의 저장 정보 포함.",
            "properties": {
              "loop_no": {
                "description": "0은 회차 시작 전 기록.",
                "type": "integer"
              },
              "plan_id": {
                "type": "string"
              },
              "revision": {
                "description": "다음 수정에서 `loop_no`와 함께 `expected_revision`으로 사용 가능.",
                "type": "integer"
              },
              "status": {
                "description": "업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.",
                "type": "string"
              }
            },
            "type": "object"
          },
          "requires_reconciliation": {
            "description": "`true`면 Rhino 또는 DB 상태를 확인해 후속 작업을 결정.",
            "type": "boolean"
          },
          "status": {
            "description": "수정 결과. 실제 변경은 updated, 무변경은 no_change, 변경과 건너뛴 항목이 함께 있으면 partial_success.",
            "enum": [
              "updated",
              "no_change",
              "partial_success",
              "error"
            ],
            "type": "string"
          },
          "step": {
            "properties": {
              "loop_no": {
                "description": "0은 회차 시작 전 기록.",
                "type": "integer"
              },
              "status": {
                "description": "업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.",
                "type": "string"
              },
              "step_id": {
                "type": "string"
              }
            },
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 62. research_01-get_construction_guidance

**CoS · beyond**

```txt
건축 구법 비교·선정을 위한 참고 자료 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "floor, wall, roof, foundation 중 선택. 빈 값은 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "include_reference_data": {
      "default": false,
      "description": "`load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.",
      "type": "boolean"
    },
    "material": {
      "default": "",
      "description": "analysis_02-validate_structure tool과 같은 재료명. `Wood`, `Steel`, `Concrete`.",
      "type": "string"
    },
    "query": {
      "default": "",
      "description": "예: `glulam`, `longspan`, `bearing wall`.",
      "type": "string"
    },
    "span_m": {
      "default": 0.0,
      "description": "0보다 크면 시스템별 `fits_span`과 경험칙에 따른 권장 부재 깊이를 계산.",
      "type": "number"
    },
    "structure_type": {
      "default": "",
      "description": "analysis_02-validate_structure tool과 같은 유형. `beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "description": "floor, wall, roof, foundation 중 선택. 빈 값은 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "include_reference_data": {
      "default": false,
      "description": "`load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.",
      "type": "boolean"
    },
    "material": {
      "default": "",
      "description": "analysis_02-validate_structure tool과 같은 재료명. `Wood`, `Steel`, `Concrete`.",
      "type": "string"
    },
    "query": {
      "default": "",
      "description": "예: `glulam`, `longspan`, `bearing wall`.",
      "type": "string"
    },
    "span_m": {
      "default": 0.0,
      "description": "0보다 크면 시스템별 `fits_span`과 경험칙에 따른 권장 부재 깊이를 계산.",
      "type": "number"
    },
    "structure_type": {
      "default": "",
      "description": "analysis_02-validate_structure tool과 같은 유형. `beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "source": {
            "description": "예비 치수 산정용 구법 라이브러리.",
            "type": "string"
          },
          "systems": {
            "items": {
              "properties": {
                "category": {
                  "type": "string"
                },
                "construction_detail": {
                  "type": "string"
                },
                "construction_reference": {
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "kind": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "depth_guidance": {
                  "items": {
                    "properties": {
                      "element": {
                        "type": "string"
                      },
                      "rule": {
                        "description": "권장 깊이 산정에 사용한 경간 비율.",
                        "type": "string"
                      },
                      "suggested_depth_mm": {
                        "type": "number"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
                },
                "fits_span": {
                  "description": "입력 경간이 경험칙 범위에 드는지 표시. 내력 판단에는 별도 구조 검토 필요.",
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "render_material_ids": {
                  "description": "의도에 맞는 재료 ID 하나를 골라 model_01-assign_material tool에 사용.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "structural_material": {
                  "type": "string"
                },
                "system_id": {
                  "description": "research_02-get_typology_narrative tool의 `construction_system` 필터 또는 재료 메타데이터에 사용.",
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 63. research_02-get_typology_narrative

**CoS · beyond**

```txt
건축 유형의 서사와 선례 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "construction_system": {
      "default": "",
      "description": "구법 라이브러리의 `system_id` 기준 필터. 예: `steel-column-frame`.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 5,
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "예: `courtyard`, `skyscraper`, `timber hall`.",
      "type": "string"
    },
    "structure_type": {
      "default": "",
      "description": "analysis_02-validate_structure tool의 유형으로 필터링. 예: `shell`, `truss`, `frame`, `membrane`.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "construction_system": {
      "default": "",
      "description": "구법 라이브러리의 `system_id` 기준 필터. 예: `steel-column-frame`.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 5,
      "type": "integer"
    },
    "query": {
      "default": "",
      "description": "예: `courtyard`, `skyscraper`, `timber hall`.",
      "type": "string"
    },
    "structure_type": {
      "default": "",
      "description": "analysis_02-validate_structure tool의 유형으로 필터링. 예: `shell`, `truss`, `frame`, `membrane`.",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "entries": {
            "items": {
              "properties": {
                "era": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                },
                "narrative": {
                  "type": "string"
                },
                "region": {
                  "type": "string"
                },
                "related_construction_systems": {
                  "description": "research_01-get_construction_guidance tool의 `query`로 검색 가능.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "typology_id": {
                  "type": "string"
                },
                "urban_role": {
                  "type": "string"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "source": {
            "type": "string"
          },
          "total": {
            "description": "`limit` 적용 전 전체 일치 수.",
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 64. research_03-search_details

**CoS · beyond**

```txt
건축 자료 디렉터리의 메타데이터 검색.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "query": {
      "default": "",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "`rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환."
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "query": {
      "default": "",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "expanded_terms": {
      "items": {},
      "type": "array"
    },
    "message": {
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "query": {
      "type": "string"
    },
    "query_terms": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "scope": {
      "type": "string"
    },
    "sources": {
      "items": {
        "properties": {
          "access": {
            "type": "string"
          },
          "formats": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "generation_use": {
            "type": "string"
          },
          "matched_terms": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "redistribution": {
            "type": "string"
          },
          "source_id": {
            "type": "string"
          },
          "terms_url": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "status": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 65. scene_01-add_objects

**CoS · beyond**

```txt
Rhino 객체를 Scene에 추가하거나 해당 Scene에서 제외한 Holon 구성원을 복원
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "object_ids": {
      "description": "일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "object_ids": {
      "description": "일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "object_ids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "already_present_indices": {
            "description": "Holon을 통해 이미 포함된 객체도 해당",
            "items": {},
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "failed_indices": {
            "description": "object_ids의 0부터 시작하는 위치",
            "items": {},
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 66. scene_02-create

**CoS · beyond**

```txt
설계 영역이나 프로그램, 상황을 나타내는 Scene 생성
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "file_name": {
      "default": "",
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외",
      "type": "string"
    },
    "name": {
      "description": "빈 이름은 Untitled scene으로 저장.",
      "type": "string"
    },
    "units": {
      "default": "mm",
      "description": "mm, cm, m, in, ft 중 선택.",
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "file_name": {
      "default": "",
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외",
      "type": "string"
    },
    "name": {
      "description": "빈 이름은 Untitled scene으로 저장.",
      "type": "string"
    },
    "units": {
      "default": "mm",
      "description": "mm, cm, m, in, ft 중 선택.",
      "type": "string"
    }
  },
  "required": [
    "name",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "scene": {
            "properties": {
              "revision": {
                "type": "integer"
              },
              "scene_id": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 67. scene_03-focus_holons

**CoS · beyond**

```txt
선택한 Holon과 하위 Holon의 유효 구성원을 Rhino에서 선택·격리·확대. 잠긴 주변 객체는 계속 보일 수 있다. Unisolate는 격리 전 표시 상태를 복원하며, 선택과 카메라 상태는 별도로 복원해야 할 수 있다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "holon_ids": {
      "description": "서로 다른 ID 1~32개. 유효 최상위 객체는 최대 4096개",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "holon_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "holon_ids": {
      "description": "서로 다른 ID 1~32개. 유효 최상위 객체는 최대 4096개",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "holon_ids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "failed_stage": {
            "description": "validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.",
            "type": "string"
          },
          "focus_observation": {
            "properties": {
              "after_failure": {
                "properties": {
                  "camera_location": {
                    "description": "문서 단위의 [x, y, z].",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "camera_target": {
                    "description": "문서 단위의 [x, y, z].",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "frustum": {
                    "description": "[left, right, bottom, top, near, far] 순서.",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 6,
                    "minItems": 6,
                    "type": "array"
                  },
                  "observation_error": {
                    "type": "string"
                  },
                  "parallel_projection": {
                    "type": "boolean"
                  },
                  "viewport_id": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "before_zoom": {
                "properties": {
                  "camera_location": {
                    "description": "문서 단위의 [x, y, z].",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "camera_target": {
                    "description": "문서 단위의 [x, y, z].",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "frustum": {
                    "description": "[left, right, bottom, top, near, far] 순서.",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 6,
                    "minItems": 6,
                    "type": "array"
                  },
                  "observation_error": {
                    "type": "string"
                  },
                  "parallel_projection": {
                    "type": "boolean"
                  },
                  "viewport_id": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "target_bounds": {
                "description": "문서 단위의 대상 합집합 경계.",
                "properties": {
                  "max": {
                    "description": "[x, y, z] 순서.",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "min": {
                    "description": "[x, y, z] 순서.",
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  }
                },
                "type": "object"
              },
              "target_bounds_error": {
                "type": "string"
              },
              "target_count": {
                "type": "integer"
              },
              "zoom_bounding_box": {
                "type": [
                  "boolean",
                  "null"
                ]
              },
              "zoom_extents_selected": {
                "type": [
                  "boolean",
                  "null"
                ]
              }
            },
            "type": "object"
          },
          "isolated": {
            "type": "boolean"
          },
          "locked_context_remains_visible": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "model_path": {
            "type": "string"
          },
          "mutation_applied": {
            "description": "null이면 뷰 변경 적용을 확인하지 못한 상태.",
            "type": [
              "boolean",
              "null"
            ]
          },
          "next_step_guide": {
            "type": "string"
          },
          "requires_reconciliation": {
            "description": "true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.",
            "type": "boolean"
          },
          "restore_visibility_command": {
            "type": "string"
          },
          "selected_ids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "status": {
            "type": "string"
          },
          "view_change": {
            "properties": {
              "display_mode_changed": {
                "type": [
                  "boolean",
                  "null"
                ]
              },
              "isolated": {
                "type": [
                  "boolean",
                  "null"
                ]
              },
              "restore_visibility_command": {
                "description": "격리 가시성만 복구. 카메라와 선택은 별도로 확인.",
                "type": "string"
              },
              "selection_changed": {
                "type": [
                  "boolean",
                  "null"
                ]
              },
              "zoom_method": {
                "description": "selected는 기본 선택 확대, bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.",
                "enum": [
                  "selected",
                  "bounding_box"
                ],
                "type": "string"
              },
              "zoom_selected": {
                "description": "선택 확대 또는 대체 경계 확대를 완료하면 true.",
                "type": [
                  "boolean",
                  "null"
                ]
              }
            },
            "type": "object"
          },
          "viewport_id": {
            "type": "string"
          },
          "zoom_selected": {
            "description": "선택 확대 또는 대체 경계 확대를 완료하면 true.",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 68. scene_04-get

**CoS · beyond**

```txt
Scene의 등록 정보와 저장된 Holon·객체 수 조회. 현재 Rhino 구성원은 scene_06-get_objects tool로 조회. include_ids=true일 때도 입력한 scene_id는 생략.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "scene": {
            "properties": {
              "direct_objects": {
                "type": "integer"
              },
              "holons": {
                "type": "integer"
              },
              "live_verified": {
                "type": "boolean"
              },
              "name": {
                "type": "string"
              },
              "objects": {
                "description": "직접 등록 또는 제외 override가 있으면 저장된 정보만으로 수를 확정하기 어려워 null 반환",
                "type": [
                  "integer",
                  "null"
                ]
              },
              "revision": {
                "type": "integer"
              },
              "units": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 69. scene_05-get_holon

**CoS · beyond**

```txt
Holon의 등록 정보와 구성원 조회. live=true로 현재 Rhino 상태를 등록 정보와 대조하고 requires_sync로 동기화 필요 여부를 확인. recursive=true는 Rhino 블록 정의 경계는 유지하며 자손 Holon을 확장. include_ids=true일 때도 입력한 holon_id는 요약에서 생략.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "holon_id": {
      "description": "include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "description": "요청한 필드 그룹에 해당하는 ID만 포함",
      "type": "boolean"
    },
    "live": {
      "default": false,
      "type": "boolean"
    },
    "recursive": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "holon_id": {
      "description": "include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "description": "요청한 필드 그룹에 해당하는 ID만 포함",
      "type": "boolean"
    },
    "live": {
      "default": false,
      "type": "boolean"
    },
    "recursive": {
      "default": false,
      "type": "boolean"
    }
  },
  "required": [
    "holon_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holon": {
            "properties": {
              "availability": {
                "description": "등록 정보와 현재 관찰 결과의 구분은 live_verified로 확인",
                "type": "string"
              },
              "live_verified": {
                "type": "boolean"
              },
              "name": {
                "type": "string"
              },
              "object_count": {
                "type": "integer"
              }
            },
            "type": "object"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 70. scene_06-get_objects

**CoS · beyond**

```txt
현재 Rhino 문서에서 Scene의 직접 객체와 Holon 구성원 조회. Scene에서 제외한 구성원은 생략.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1~200",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "type": "integer"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1~200",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "type": "integer"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "live_verified": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "model_path": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "objects": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "offset": {
            "type": "integer"
          },
          "status": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "description": "true이면 같은 조건에서 offset을 반환한 objects의 길이만큼 늘려 다음 페이지 조회",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 71. scene_07-list

**CoS · beyond**

```txt
공유 프로젝트 DB의 Scene 목록 조회. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "file_name": {
      "default": "",
      "description": "확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1~200",
      "type": "integer"
    },
    "name": {
      "default": "",
      "description": "대소문자를 구분하지 않는 부분 검색",
      "type": "string"
    },
    "offset": {
      "default": 0,
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "file_name": {
      "default": "",
      "description": "확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회",
      "type": "string"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1~200",
      "type": "integer"
    },
    "name": {
      "default": "",
      "description": "대소문자를 구분하지 않는 부분 검색",
      "type": "string"
    },
    "offset": {
      "default": 0,
      "type": "integer"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "limit": {
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "offset": {
            "type": "integer"
          },
          "scenes": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "status": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          },
          "truncated": {
            "description": "true이면 같은 필터에서 offset을 반환한 scenes의 길이만큼 늘려 다음 페이지 조회",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 72. scene_08-list_holons

**CoS · beyond**

```txt
모델에서 저장된 Holon 등록 목록 조회. Scene을 지정하면 연결된 Holon을, 생략하면 기본으로 최상위 Holon을 조회. recursive=true는 자손을 포함하며 이 자손은 Scene에 직접 등록되지 않았을 수 있다. 현재 Rhino 구성원은 scene_05-get_holon tool에서 live=true로 조회.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "관리형 세션에서 생략하면 연결된 모델 기준",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "recursive": {
      "default": false,
      "type": "boolean"
    },
    "scene_id": {
      "default": "",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "관리형 세션에서 생략하면 연결된 모델 기준",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회"
    },
    "include_ids": {
      "default": false,
      "type": "boolean"
    },
    "recursive": {
      "default": false,
      "type": "boolean"
    },
    "scene_id": {
      "default": "",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holons": {
            "items": {
              "type": "object"
            },
            "type": "array"
          },
          "live_verified": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "total": {
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 73. scene_09-remove_holon

**CoS · beyond**

```txt
Holon 등록 해제. Rhino 형상과 그룹은 보존.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_id": {
      "description": "이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제",
      "type": "string"
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "holon_id": {
      "description": "이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제",
      "type": "string"
    }
  },
  "required": [
    "holon_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holon": {
            "properties": {
              "holon_id": {
                "type": "string"
              },
              "live_verified": {
                "type": "boolean"
              },
              "status": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 74. scene_10-remove_objects

**CoS · beyond**

```txt
객체를 Scene에서 제외. Rhino 형상과 Holon 그룹은 보존.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "object_ids": {
      "description": "일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "object_ids": {
      "description": "일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "object_ids",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "already_absent_indices": {
            "description": "object_ids의 0부터 시작하는 위치",
            "items": {},
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "failed_indices": {
            "description": "object_ids의 0부터 시작하는 위치",
            "items": {},
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 75. scene_11-sync_holon

**CoS · beyond**

```txt
현재 Rhino 구성원으로 Holon 등록 정보 갱신
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "default": "",
      "type": "string"
    },
    "holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "holon_id 또는 rhino_group_id와 동시 지정 불가"
    },
    "rhino_group_id": {
      "default": "",
      "description": "holon_id와 함께 지정해 현재 Rhino 그룹 GUID가 일치하는지 확인하는 용도",
      "type": "string"
    },
    "scene_id": {
      "default": "",
      "description": "holon_id, holon_ids, rhino_group_id와 동시 지정 불가",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "default": "",
      "type": "string"
    },
    "holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "holon_id 또는 rhino_group_id와 동시 지정 불가"
    },
    "rhino_group_id": {
      "default": "",
      "description": "holon_id와 함께 지정해 현재 Rhino 그룹 GUID가 일치하는지 확인하는 용도",
      "type": "string"
    },
    "scene_id": {
      "default": "",
      "description": "holon_id, holon_ids, rhino_group_id와 동시 지정 불가",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "changed": {
            "description": "등록 내용이 바뀐 항목만 계산하며 변경이 없으면 리비전 유지",
            "type": "integer"
          },
          "checked": {
            "type": "integer"
          },
          "error_code": {
            "type": "string"
          },
          "live_verified": {
            "description": "모든 대상의 현재 Rhino 상태를 문제 없이 확인한 경우 true",
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "problems": {
            "description": "문제 항목과 무관한 유효 등록은 함께 갱신될 수 있음",
            "items": {},
            "type": "array"
          },
          "scene_revisions": {
            "properties": {},
            "type": "object"
          },
          "status": {
            "type": "string"
          },
          "unavailable": {
            "description": "present 이외 상태의 등록 수",
            "type": "integer"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 76. scene_12-update

**CoS · beyond**

```txt
Scene의 프로젝트 파일 연결 변경 또는 해제
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "file_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명. 빈 문자열은 연결 해제, 생략하거나 null이면 기존 연결 유지"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "file_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명. 빈 문자열은 연결 해제, 생략하거나 null이면 기존 연결 유지"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "scene_id",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "scene": {
            "properties": {
              "revision": {
                "description": "파일 연결이 실제로 바뀔 때 증가",
                "type": "integer"
              },
              "scene_id": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 77. scene_13-upsert_holon

**CoS · beyond**

```txt
물리적 요소와 관계를 Holon으로 등록하거나 갱신
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "child_holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "default": "",
      "description": "생략하면 새 Holon 등록",
      "type": "string"
    },
    "name": {
      "description": "기존 Rhino 그룹을 연결할 때는 그룹의 정확한 이름과 일치해야 함",
      "type": "string"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용"
    },
    "rhino_group_id": {
      "default": "",
      "description": "동명 Rhino 그룹을 구분할 때 사용",
      "type": "string"
    },
    "scene_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지"
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "child_holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "default": "",
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "default": "",
      "description": "생략하면 새 Holon 등록",
      "type": "string"
    },
    "name": {
      "description": "기존 Rhino 그룹을 연결할 때는 그룹의 정확한 이름과 일치해야 함",
      "type": "string"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용"
    },
    "rhino_group_id": {
      "default": "",
      "description": "동명 Rhino 그룹을 구분할 때 사용",
      "type": "string"
    },
    "scene_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지"
    }
  },
  "required": [
    "name",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "holon": {
            "properties": {
              "availability": {
                "type": "string"
              },
              "holon_id": {
                "type": "string"
              },
              "live_verified": {
                "type": "boolean"
              },
              "object_count": {
                "type": "integer"
              }
            },
            "type": "object"
          },
          "message": {
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 78. script_01-run_project_python

**CoS · beyond**

```txt
연결된 Rhino 문서에서 Python 3 코드로 형상을 편집하거나 산출물을 생성. 선택한 Plan·Loop 산출물 폴더가 작업 디렉터리. 쓰기 가능한 공간을 plan_10-set_working tool으로 선택하거나 기존 선택을 재사용한다.

스크립트 실행만 기록할 때는 출력 또는 반환값에 executed를 사용한다. 작업 목적의 달성 여부는 실제 변경과 산출물로 확인하고, 문서 저장 여부는 별도로 확인한다. 시간 초과 뒤에도 실행이 이어지거나 오류 시 부분 변경이 남을 수 있다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "description": "동기식 코드. doc과 scriptcontext.doc은 연결된 문서. JSON 호환 반환값은 result에 할당하고 상대 경로는 선택한 산출물 폴더 기준",
      "type": "string"
    },
    "timeout_seconds": {
      "default": 60,
      "description": "완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.",
      "type": "integer"
    }
  },
  "required": [
    "code"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "description": "동기식 코드. doc과 scriptcontext.doc은 연결된 문서. JSON 호환 반환값은 result에 할당하고 상대 경로는 선택한 산출물 폴더 기준",
      "type": "string"
    },
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "timeout_seconds": {
      "default": 60,
      "description": "완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.",
      "type": "integer"
    }
  },
  "required": [
    "code",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "type": [
        "string",
        "null"
      ]
    },
    "completed": {
      "type": "boolean"
    },
    "completion_state": {
      "description": "finishing은 Rhino 완료 후 CLI 종료 대기, awaiting_receipt는 CLI 종료 후 Rhino 완료 근거 대기.",
      "type": "string"
    },
    "connection_state": {
      "description": "recovering이면 실행 확인과 최초 호출의 정리가 진행 중",
      "type": "string"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "mutation_state": {
      "description": "partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인",
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "pending": {
      "description": "true이면 같은 request_id로 script_03-get_execution tool 조회",
      "type": "boolean"
    },
    "request_id": {
      "description": "미완료 실행, 불확실한 결과 또는 다음 결과 페이지를 script_03-get_execution tool로 조회할 때 사용",
      "type": "string"
    },
    "result": {},
    "result_display_error": {
      "type": [
        "string",
        "null"
      ]
    },
    "result_error": {
      "type": [
        "string",
        "null"
      ]
    },
    "result_page": {
      "properties": {
        "available_fields": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "pages": {
          "additionalProperties": {
            "properties": {
              "next_offset": {
                "type": [
                  "integer",
                  "null"
                ]
              },
              "offset": {
                "type": "integer"
              },
              "returned": {
                "type": "integer"
              },
              "total": {
                "type": "integer"
              }
            },
            "type": "object"
          },
          "description": "배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회",
          "type": "object"
        },
        "type": {
          "type": "string"
        },
        "unit": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "status": {
      "description": "executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 result와 mutation_state에서 별도 확인",
      "type": "string"
    },
    "timed_out": {
      "description": "첫 응답 대기 한도 초과. 이때 실행이 이어지거나 부분 변경이 남을 수 있음",
      "type": "boolean"
    },
    "uncertain": {
      "description": "완료 근거 미확인. 재실행 전 문서 상태 확인 필요",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>


### 79. script_02-run_rhino

**CoS · beyond**

```txt
연결된 RhinoCode에서 모델링·편집·측정 코드 또는 명령 매크로 실행. 실행 완료만 기록할 때는 출력 또는 반환값에 executed를 사용하고, 작업 결과는 result와 mutation_state에서 확인한다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "language": {
      "default": "python",
      "description": "python(Python 3), python2, csharp, csharp-script, command 중 선택.",
      "type": "string"
    },
    "script": {
      "description": "동기식 Python 소스, C# 문장 본문 또는 명령 매크로. Python은 JSON 호환 값을 result에, C#은 JSON을 result_json에 할당. doc은 연결된 문서. command는 !·Pause·대화상자 없이 종료되는 매크로",
      "type": "string"
    },
    "timeout_seconds": {
      "default": 60,
      "description": "완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.",
      "type": "integer"
    }
  },
  "required": [
    "script"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "language": {
      "default": "python",
      "description": "python(Python 3), python2, csharp, csharp-script, command 중 선택.",
      "type": "string"
    },
    "script": {
      "description": "동기식 Python 소스, C# 문장 본문 또는 명령 매크로. Python은 JSON 호환 값을 result에, C#은 JSON을 result_json에 할당. doc은 연결된 문서. command는 !·Pause·대화상자 없이 종료되는 매크로",
      "type": "string"
    },
    "timeout_seconds": {
      "default": 60,
      "description": "완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.",
      "type": "integer"
    }
  },
  "required": [
    "script",
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "completed": {
            "type": "boolean"
          },
          "completion_state": {
            "description": "finishing은 Rhino 완료 후 CLI 종료 대기, awaiting_receipt는 CLI 종료 후 Rhino 완료 근거 대기.",
            "type": "string"
          },
          "connection_state": {
            "description": "recovering이면 실행 확인과 최초 호출의 정리가 진행 중",
            "type": "string"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "description": "partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인",
            "type": "string"
          },
          "next_step_guide": {
            "type": "string"
          },
          "pending": {
            "description": "true이면 같은 request_id로 script_03-get_execution tool 조회",
            "type": "boolean"
          },
          "request_id": {
            "description": "같은 실행을 script_03-get_execution tool로 조회할 때 사용",
            "type": "string"
          },
          "result": {},
          "result_display_error": {
            "type": [
              "string",
              "null"
            ]
          },
          "result_error": {
            "type": [
              "string",
              "null"
            ]
          },
          "result_page": {
            "properties": {
              "available_fields": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "pages": {
                "additionalProperties": {
                  "properties": {
                    "next_offset": {
                      "type": [
                        "integer",
                        "null"
                      ]
                    },
                    "offset": {
                      "type": "integer"
                    },
                    "returned": {
                      "type": "integer"
                    },
                    "total": {
                      "type": "integer"
                    }
                  },
                  "type": "object"
                },
                "description": "배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회",
                "type": "object"
              },
              "type": {
                "type": "string"
              },
              "unit": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "status": {
            "description": "executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 result와 mutation_state에서 별도 확인",
            "type": "string"
          },
          "timed_out": {
            "description": "첫 응답 대기 한도 초과. 이때 실행이 이어지거나 부분 변경이 남을 수 있음",
            "type": "boolean"
          },
          "uncertain": {
            "description": "완료 근거 미확인. 재실행 전 문서 상태 확인 필요",
            "type": "boolean"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>


### 80. script_03-get_execution

**CoS · beyond**

```txt
이전 RhinoCode 실행의 상태와 보관된 결과·로그 조회. 조회는 실행 기록만 읽으며, 연결이 끝난 뒤에도 기록이 남아 있으면 조회할 수 있다. 배열이나 문자열 결과는 페이지로 조회하고 로그는 별도의 바이트 오프셋을 사용한다.
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_diagnostics": {
      "default": false,
      "type": "boolean"
    },
    "include_ids": {
      "default": true,
      "type": "boolean"
    },
    "include_result": {
      "default": true,
      "type": "boolean"
    },
    "include_stdout": {
      "default": false,
      "description": "stdout·stderr와 CLI 로그 포함",
      "type": "boolean"
    },
    "limit": {
      "default": 100,
      "description": "결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위",
      "type": "integer"
    },
    "request_id": {
      "default": "",
      "description": "생략하면 현재 연결의 최근 실행 조회. beyond·CoS에서 지정한 ID로 최초 실행 연결을 찾으며, 시간 초과 후에는 같은 ID를 지정",
      "type": "string"
    },
    "result_fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_diagnostics": {
      "default": false,
      "type": "boolean"
    },
    "include_ids": {
      "default": true,
      "type": "boolean"
    },
    "include_result": {
      "default": true,
      "type": "boolean"
    },
    "include_stdout": {
      "default": false,
      "description": "stdout·stderr와 CLI 로그 포함",
      "type": "boolean"
    },
    "limit": {
      "default": 100,
      "description": "결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위",
      "type": "integer"
    },
    "request_id": {
      "default": "",
      "description": "생략하면 현재 연결의 최근 실행 조회. beyond·CoS에서 지정한 ID로 최초 실행 연결을 찾으며, 시간 초과 후에는 같은 ID를 지정",
      "type": "string"
    },
    "result_fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "completed": {
      "description": "최종 Rhino 처리 근거와 CLI 종료를 모두 확인한 경우 true. native_completed는 Rhino 측 완료 확인",
      "type": "boolean"
    },
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "mutation_state": {
      "description": "partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인",
      "type": "string"
    },
    "next_step_guide": {
      "type": "string"
    },
    "request_id": {
      "description": "같은 실행의 상태나 다음 결과 페이지를 조회할 때 사용",
      "type": "string"
    },
    "result": {},
    "result_display_error": {
      "type": [
        "string",
        "null"
      ]
    },
    "result_error": {
      "type": [
        "string",
        "null"
      ]
    },
    "result_page": {
      "properties": {
        "available_fields": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "pages": {
          "additionalProperties": {
            "properties": {
              "next_offset": {
                "type": [
                  "integer",
                  "null"
                ]
              },
              "offset": {
                "type": "integer"
              },
              "returned": {
                "type": "integer"
              },
              "total": {
                "type": "integer"
              }
            },
            "type": "object"
          },
          "description": "배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회",
          "type": "object"
        },
        "type": {
          "type": "string"
        },
        "unit": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "status": {
      "description": "executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 별도 확인",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>


### 81. script_04-save_document

**CoS · beyond**

```txt
사용자의 영구 저장 요청에 따라 연결된 문서 전체를 기존 .3dm 경로에 저장
```

<details><summary>CoS 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {},
  "type": "object"
}
```

</details>

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "description": "이 대화에서 connect_02-session tool 또는 connect_03-start_session tool로 받은 연결 ID.",
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>CoS · beyond 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "modified": {
            "type": "boolean"
          },
          "next_step_guide": {
            "type": "string"
          },
          "saved": {
            "description": "저장이 미확정이면 null과 requires_reconciliation=true를 반환. 재호출 전 현재 문서 상태 확인",
            "type": [
              "boolean",
              "null"
            ]
          },
          "status": {
            "type": "string"
          }
        },
        "type": "object"
      },
      "type": "string"
    }
  },
  "required": [
    "result"
  ],
  "type": "object",
  "x-fastmcp-wrap-result": true
}
```

</details>

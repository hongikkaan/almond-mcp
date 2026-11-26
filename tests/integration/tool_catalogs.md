# 현행 툴 선언

beyond와 RhinoTerminal의 `tools/list`에서 읽은 설명과 입출력 스키마다. 공통 값은 한 번만 표시한다. 각 해시는 도구를 이름순으로 정렬하고 객체 키를 정렬한 뒤, 공백과 유니코드 이스케이프 없이 UTF-8 JSON으로 직렬화한 전체 배열에서 계산한다.

- beyond 도구 81개, 선언 SHA-256 `ba801708e14b50c60349b48855cb2c5f36634b20f2b708d3c553285aedda4711`
- RhinoTerminal 도구 76개, 선언 SHA-256 `c1d8d43918da0e678f29a80d9bf1a67c7602bc7a3466cb36d41012649ed3f7e5`

### 1. analysis_01-list_design_codes

**beyond · RhinoTerminal**

```txt
구조 해석의 설계기준 프로필 조회. 프로필 ID는 해석·시각화의 design_code에 전달한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "parameters",
              "source",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "기본은 요약. 수치와 조합식은 `parameters`로 요청."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "parameters",
              "source",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "기본은 요약. 수치와 조합식은 `parameters`로 요청."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "default": {
            "type": "string"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "problems": {
            "description": "로딩 중 거절된 사용자 프로필의 문제.",
            "items": {
              "type": "string"
            },
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
                  "description": "구조 해석·시각화의 `design_code`에 전달.",
                  "type": "string"
                },
                "imposed_floor_kn_m2": {
                  "additionalProperties": {
                    "type": "number"
                  },
                  "description": "용도별 권장 활하중.",
                  "type": "object"
                },
                "name": {
                  "type": "string"
                },
                "uls_default": {
                  "type": "string"
                },
                "uls_expression": {
                  "type": "string"
                },
                "unverified": {
                  "description": "확인되지 않은 프로필 항목. 빈 배열이면 모든 항목을 확인했다.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                }
              },
              "required": [
                "id",
                "unverified"
              ],
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

**beyond · RhinoTerminal**

```txt
Rhino 구조 형상을 해석하고 설계기준을 검토한다. 실제 엔진과 적용 입력은 실행 이력에 기록한다. 엔진·경고·가정과 미검증 설계기준 값을 함께 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "description": "native에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 하중과 중복을 피한다.",
      "type": "boolean"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "connections": {
      "description": "기본 rigid. simple은 보 강축·가새 양축의 단부 휨을 해제하고 동축 부재·기둥의 연속성을 유지.\n곡선 User Text의 release(pinned, pinned_start, pinned_end, rigid)가 우선.",
      "type": "string"
    },
    "design_basis": {
      "description": "기본 en1990은 선택 프로필의 SLS·ULS 조합 적용. unfactored는 양쪽에 G + Q 사용.",
      "type": "string"
    },
    "design_code": {
      "description": "analysis_01-list_design_codes tool의 프로필 ID. 기본 eurocode, off는 비계수 G + Q.",
      "type": "string"
    },
    "detail": {
      "description": "네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.",
      "type": "boolean"
    },
    "engine": {
      "description": "기본 auto는 native 프레임 해석 우선. 셸·그리드셸·막 구조 또는 지원 불가 형상은 Karamba.\nkaramba는 api → template → rule_based 순. 실제 경로는 analysis_method와 warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "description": "강재 중공 단면 제작 방식. 기본 cold_formed는 좌굴 곡선 c, hot_finished는 a(S460은 a0).",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점. · 기본값 true",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "description": "바닥 구성층·마감의 추가 고정하중. 기본값 0.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "description": "native 바닥 구획의 용도별 활하중. 45° 양방향 분담, 장단변비가 2:1을 넘으면 일방향. 기본값 0.\n가구·재실자 하중이 중복되지 않게 asset_loads와 load_kn을 조정.",
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
      "description": "전체 추가 하중. native는 자유 절점에 하향(-Z) 균등 분배. 기본 10, 바닥·자산 하중으로 충당 시 0.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". · 기본값 \"Steel\"",
      "type": "string"
    },
    "self_weight": {
      "default": true,
      "description": "기본값 true",
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
      "description": "여러 절점으로 분할한 부재의 처짐 검토용 전체 경간."
    },
    "stability": {
      "description": "기본 auto는 초기 불완전성을 반영하고 alpha_cr < 10에서 2차 해석, ≤ 1이면 불안정.\noff는 초기 불완전성을 생략하는 1차 해석.",
      "type": "string"
    },
    "structure_type": {
      "description": "beam(기본), truss, shell, frame, canopy, gridshell, membrane, highrise.",
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
      "description": "6.10 또는 6.10ab(부재별로 더 불리한 6.10a/b). 프로필 고정식이 우선하며 충돌 시 경고."
    }
  },
  "required": [
    "connection_id",
    "guids"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "description": "native에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 하중과 중복을 피한다.",
      "type": "boolean"
    },
    "connections": {
      "description": "기본 rigid. simple은 보 강축·가새 양축의 단부 휨을 해제하고 동축 부재·기둥의 연속성을 유지.\n곡선 User Text의 release(pinned, pinned_start, pinned_end, rigid)가 우선.",
      "type": "string"
    },
    "design_basis": {
      "description": "기본 en1990은 선택 프로필의 SLS·ULS 조합 적용. unfactored는 양쪽에 G + Q 사용.",
      "type": "string"
    },
    "design_code": {
      "description": "analysis_01-list_design_codes tool의 프로필 ID. 기본 eurocode, off는 비계수 G + Q.",
      "type": "string"
    },
    "detail": {
      "description": "네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.",
      "type": "boolean"
    },
    "engine": {
      "description": "기본 auto는 native 프레임 해석 우선. 셸·그리드셸·막 구조 또는 지원 불가 형상은 Karamba.\nkaramba는 api → template → rule_based 순. 실제 경로는 analysis_method와 warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "description": "강재 중공 단면 제작 방식. 기본 cold_formed는 좌굴 곡선 c, hot_finished는 a(S460은 a0).",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점. · 기본값 true",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "description": "바닥 구성층·마감의 추가 고정하중. 기본값 0.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "description": "native 바닥 구획의 용도별 활하중. 45° 양방향 분담, 장단변비가 2:1을 넘으면 일방향. 기본값 0.\n가구·재실자 하중이 중복되지 않게 asset_loads와 load_kn을 조정.",
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
      "description": "전체 추가 하중. native는 자유 절점에 하향(-Z) 균등 분배. 기본 10, 바닥·자산 하중으로 충당 시 0.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". · 기본값 \"Steel\"",
      "type": "string"
    },
    "self_weight": {
      "default": true,
      "description": "기본값 true",
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
      "description": "여러 절점으로 분할한 부재의 처짐 검토용 전체 경간."
    },
    "stability": {
      "description": "기본 auto는 초기 불완전성을 반영하고 alpha_cr < 10에서 2차 해석, ≤ 1이면 불안정.\noff는 초기 불완전성을 생략하는 1차 해석.",
      "type": "string"
    },
    "structure_type": {
      "description": "beam(기본), truss, shell, frame, canopy, gridshell, membrane, highrise.",
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
      "description": "6.10 또는 6.10ab(부재별로 더 불리한 6.10a/b). 프로필 고정식이 우선하며 충돌 시 경고."
    }
  },
  "required": [
    "guids"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
            "type": "string"
          },
          "design_code": {
            "properties": {
              "id": {
                "type": "string"
              },
              "unverified": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "members": {
            "description": "native에서 `detail: true`일 때 부재별 상세 검토.",
            "items": {
              "properties": {
                "buckling_curves": {
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
                  ]
                },
                "buckling_length_m": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "buckling_utilization": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "chi": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "chi_y": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "chi_z": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "cm_y": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "cm_z": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "cross_section_utilization": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "deflection_mm": {
                  "type": "number"
                },
                "deflection_ratio": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "elements": {
                  "type": "integer"
                },
                "end_m": {
                  "items": {
                    "type": "number"
                  },
                  "maxItems": 3,
                  "minItems": 3,
                  "type": "array"
                },
                "eq_6_61": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "eq_6_62": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "governing_check": {
                  "type": "string"
                },
                "governing_combination": {
                  "type": "string"
                },
                "id": {
                  "type": "string"
                },
                "kyy": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "kzz": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "lambda_y": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "lambda_z": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "layer": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "length_m": {
                  "type": "number"
                },
                "m_max_knm": {
                  "type": "number"
                },
                "material": {
                  "type": "string"
                },
                "max_displacement_mm": {
                  "type": "number"
                },
                "max_stress_mpa": {
                  "type": "number"
                },
                "moduli": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "n_compression_kn": {
                  "type": "number"
                },
                "n_tension_kn": {
                  "type": "number"
                },
                "pinned_ends": {
                  "properties": {
                    "end": {
                      "type": "boolean"
                    },
                    "start": {
                      "type": "boolean"
                    }
                  },
                  "type": "object"
                },
                "role": {
                  "type": "string"
                },
                "section": {
                  "type": "string"
                },
                "section_class": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "slenderness": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "source_guids": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "start_m": {
                  "items": {
                    "type": "number"
                  },
                  "maxItems": 3,
                  "minItems": 3,
                  "type": "array"
                },
                "status": {
                  "type": "string"
                },
                "t_max_knm": {
                  "type": "number"
                },
                "utilization": {
                  "type": "number"
                },
                "v_max_kn": {
                  "type": "number"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "passed": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "indicative 해석에서는 판정이 없을 수 있음(null). 구조 안전 인증은 별도."
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
          "supports": {
            "items": {
              "properties": {
                "node": {
                  "type": "integer"
                },
                "position_m": {
                  "items": {
                    "type": "number"
                  },
                  "type": "array"
                },
                "restraint": {
                  "type": "string"
                },
                "sls": {
                  "additionalProperties": {
                    "type": "number"
                  },
                  "type": "object"
                },
                "uls": {
                  "additionalProperties": {
                    "additionalProperties": {
                      "type": "number"
                    },
                    "type": "object"
                  },
                  "type": "object"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "warnings": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "worst_member_guids": {
            "description": "사용률 상위 최대 5개. 시각화의 `display_guids`에 전달.",
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

**beyond · RhinoTerminal**

```txt
구조 해석의 임시 뷰포트 오버레이를 표시한다. `clear: true`로 제거한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "description": "native에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 하중과 중복을 피한다.",
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
      "description": "외경을 지정했을 때 기본 두께는 외경의 1/20."
    },
    "clear": {
      "type": "boolean"
    },
    "color_by": {
      "default": "displacement",
      "description": "\"displacement\" 또는 \"utilization\". · 기본값 \"displacement\"",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "connections": {
      "description": "기본 rigid. simple은 보 강축·가새 양축의 단부 휨을 해제하고 동축 부재·기둥의 연속성을 유지.\n곡선 User Text의 release(pinned, pinned_start, pinned_end, rigid)가 우선.",
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
      "description": "L/n의 n. 생략하면 설계기준 한계 사용."
    },
    "design_basis": {
      "description": "기본 en1990은 선택 프로필의 SLS·ULS 조합 적용. unfactored는 양쪽에 G + Q 사용.",
      "type": "string"
    },
    "design_code": {
      "description": "analysis_01-list_design_codes tool의 프로필 ID. 기본 eurocode, off는 비계수 G + Q.",
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
      "description": "오버레이 대상 부재만 지정. 해석에는 `guids` 전체 사용."
    },
    "engine": {
      "description": "기본 auto는 native 프레임 해석 우선. 셸·그리드셸·막 구조 또는 지원 불가 형상은 Karamba.\nkaramba는 api → template → rule_based 순. 실제 경로는 analysis_method와 warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "description": "강재 중공 단면 제작 방식. 기본 cold_formed는 좌굴 곡선 c, hot_finished는 a(S460은 a0).",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점. · 기본값 true",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "description": "바닥 구성층·마감의 추가 고정하중. 기본값 0.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "description": "native 바닥 구획의 용도별 활하중. 45° 양방향 분담, 장단변비가 2:1을 넘으면 일방향. 기본값 0.\n가구·재실자 하중이 중복되지 않게 asset_loads와 load_kn을 조정.",
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
      "description": "clear일 때만 생략 가능. 축선 곡선과 지점 점 GUID. 지점 점이 없으면 최하단 절점을 사용한다."
    },
    "load_kn": {
      "description": "전체 추가 하중. native는 자유 절점에 하향(-Z) 균등 분배. 기본 10, 바닥·자산 하중으로 충당 시 0.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". · 기본값 \"Steel\"",
      "type": "string"
    },
    "physics": {
      "description": "false면 변형 없이 표시. 기본값 true.",
      "type": "boolean"
    },
    "reanalyze": {
      "description": "false면 현재 오버레이의 해석을 재사용해 표시만 갱신. 오버레이가 없으면 오류. 기본값 true.",
      "type": "boolean"
    },
    "reveal": {
      "default": 1,
      "description": "표시할 부재 비율 0..1. 단계별 시공 재생에 사용. · 기본값 1.0",
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
      "description": "변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정."
    },
    "self_weight": {
      "default": true,
      "description": "기본값 true",
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
      "description": "여러 절점으로 분할한 부재의 처짐 검토용 전체 경간."
    },
    "stability": {
      "description": "기본 auto는 초기 불완전성을 반영하고 alpha_cr < 10에서 2차 해석, ≤ 1이면 불안정.\noff는 초기 불완전성을 생략하는 1차 해석.",
      "type": "string"
    },
    "title": {
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
      "description": "6.10 또는 6.10ab(부재별로 더 불리한 6.10a/b). 프로필 고정식이 우선하며 충돌 시 경고."
    },
    "view": {
      "description": "deflection은 처짐, buckling은 native 해석의 첫 ULS 조합에 대한 좌굴 모드와 alpha_cr을 표시한다.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_loads": {
      "description": "native에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 하중과 중복을 피한다.",
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
      "description": "외경을 지정했을 때 기본 두께는 외경의 1/20."
    },
    "clear": {
      "type": "boolean"
    },
    "color_by": {
      "default": "displacement",
      "description": "\"displacement\" 또는 \"utilization\". · 기본값 \"displacement\"",
      "type": "string"
    },
    "connections": {
      "description": "기본 rigid. simple은 보 강축·가새 양축의 단부 휨을 해제하고 동축 부재·기둥의 연속성을 유지.\n곡선 User Text의 release(pinned, pinned_start, pinned_end, rigid)가 우선.",
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
      "description": "L/n의 n. 생략하면 설계기준 한계 사용."
    },
    "design_basis": {
      "description": "기본 en1990은 선택 프로필의 SLS·ULS 조합 적용. unfactored는 양쪽에 G + Q 사용.",
      "type": "string"
    },
    "design_code": {
      "description": "analysis_01-list_design_codes tool의 프로필 ID. 기본 eurocode, off는 비계수 G + Q.",
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
      "description": "오버레이 대상 부재만 지정. 해석에는 `guids` 전체 사용."
    },
    "engine": {
      "description": "기본 auto는 native 프레임 해석 우선. 셸·그리드셸·막 구조 또는 지원 불가 형상은 Karamba.\nkaramba는 api → template → rule_based 순. 실제 경로는 analysis_method와 warnings에서 확인.",
      "type": "string"
    },
    "fabrication": {
      "description": "강재 중공 단면 제작 방식. 기본 cold_formed는 좌굴 곡선 c, hot_finished는 a(S460은 a0).",
      "type": "string"
    },
    "fixed_supports": {
      "default": true,
      "description": "true는 완전 고정, false는 회전이 자유로운 핀 지점. · 기본값 true",
      "type": "boolean"
    },
    "floor_dead_kn_m2": {
      "description": "바닥 구성층·마감의 추가 고정하중. 기본값 0.",
      "type": "number"
    },
    "floor_load_kn_m2": {
      "description": "native 바닥 구획의 용도별 활하중. 45° 양방향 분담, 장단변비가 2:1을 넘으면 일방향. 기본값 0.\n가구·재실자 하중이 중복되지 않게 asset_loads와 load_kn을 조정.",
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
      "description": "clear일 때만 생략 가능. 축선 곡선과 지점 점 GUID. 지점 점이 없으면 최하단 절점을 사용한다."
    },
    "load_kn": {
      "description": "전체 추가 하중. native는 자유 절점에 하향(-Z) 균등 분배. 기본 10, 바닥·자산 하중으로 충당 시 0.",
      "type": "number"
    },
    "material": {
      "default": "Steel",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". · 기본값 \"Steel\"",
      "type": "string"
    },
    "physics": {
      "description": "false면 변형 없이 표시. 기본값 true.",
      "type": "boolean"
    },
    "reanalyze": {
      "description": "false면 현재 오버레이의 해석을 재사용해 표시만 갱신. 오버레이가 없으면 오류. 기본값 true.",
      "type": "boolean"
    },
    "reveal": {
      "default": 1,
      "description": "표시할 부재 비율 0..1. 단계별 시공 재생에 사용. · 기본값 1.0",
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
      "description": "변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정."
    },
    "self_weight": {
      "default": true,
      "description": "기본값 true",
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
      "description": "여러 절점으로 분할한 부재의 처짐 검토용 전체 경간."
    },
    "stability": {
      "description": "기본 auto는 초기 불완전성을 반영하고 alpha_cr < 10에서 2차 해석, ≤ 1이면 불안정.\noff는 초기 불완전성을 생략하는 1차 해석.",
      "type": "string"
    },
    "title": {
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
      "description": "6.10 또는 6.10ab(부재별로 더 불리한 6.10a/b). 프로필 고정식이 우선하며 충돌 시 경고."
    },
    "view": {
      "description": "deflection은 처짐, buckling은 native 해석의 첫 ULS 조합에 대한 좌굴 모드와 alpha_cr을 표시한다.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "buckling": {
            "properties": {
              "alpha_cr": {
                "type": "number"
              },
              "combination": {
                "type": "string"
              }
            },
            "required": [
              "alpha_cr"
            ],
            "type": "object"
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
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
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
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ]
          },
          "message": {
            "type": "string"
          },
          "nodes": {
            "type": "integer"
          },
          "passed": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "null이면 참고 해석 결과로 재료 내력 판정은 생략."
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

**beyond · RhinoTerminal**

```txt
구조 검증 이력의 Markdown 보고서를 저장한다. 실제 엔진·입력과 과거 미기록 입력의 상태를 담는다. 이력이 없으면 analysis_02-validate_structure tool을 먼저 호출한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "limit": {
      "default": 50,
      "description": "최대 500회. · 기본값 50",
      "type": "integer"
    },
    "path": {
      "description": "관리형은 선택한 Plan 산출물 폴더 기준 상대 경로. 기본 reports/structural-validation.md.\n독립 실행의 기본은 사용자 데이터 아래 reports/structural-validation-<timestamp>.md.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "limit": {
      "default": 50,
      "description": "최대 500회. · 기본값 50",
      "type": "integer"
    },
    "path": {
      "description": "관리형은 선택한 Plan 산출물 폴더 기준 상대 경로. 기본 reports/structural-validation.md.\n독립 실행의 기본은 사용자 데이터 아래 reports/structural-validation-<timestamp>.md.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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

**beyond · RhinoTerminal**

```txt
직접 측정한 층 경계·출구 중심·유효 폭·경로 길이로 피난 조건을 예비 검토한다. 보행거리와 스프링클러 설치 구역의 막다른 복도는 업무용 기준을 적용하므로 `basis`·`source_note`·`warnings`를 적용 법규와 대조한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "dead_end_m": {
      "default": 0,
      "description": "가장 긴 막다른 복도 길이. 0이면 검사 생략. · 기본값 0.0",
      "type": "number"
    },
    "exits": {
      "description": "문 하나당 한 항목. 중심 좌표와 유효 폭을 mm로 지정.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "name": {
            "type": "string"
          },
          "width_mm": {
            "type": "number"
          },
          "x_mm": {
            "type": "number"
          },
          "y_mm": {
            "type": "number"
          }
        },
        "required": [
          "x_mm",
          "y_mm",
          "width_mm"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "net_area_m2": {
      "description": "실제 재실 면적. 생략 또는 0이면 경계의 직사각형 면적.",
      "type": "number"
    },
    "occupancy": {
      "default": "business",
      "description": "business, mercantile, assembly_unconcentrated, classroom, residential, storage. · 기본값 \"business\"",
      "type": "string"
    },
    "plate_bounds_mm": {
      "description": "층 바닥 경계 [min_x, min_y, max_x, max_y].",
      "items": {
        "type": "number"
      },
      "maxItems": 4,
      "minItems": 4,
      "type": "array"
    },
    "sprinklered": {
      "default": true,
      "description": "전체 구역 설치 기준. · 기본값 true",
      "type": "boolean"
    },
    "stories": {
      "description": "출구가 담당하는 층수. 기본 1. 2층 이상은 최소 2개 출구와 계단 폭 기준 적용.",
      "type": "integer"
    },
    "travel_distances_m": {
      "description": "입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략. · 기본값 []",
      "items": {
        "type": "number"
      },
      "type": "array"
    }
  },
  "required": [
    "connection_id",
    "exits",
    "plate_bounds_mm"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "dead_end_m": {
      "default": 0,
      "description": "가장 긴 막다른 복도 길이. 0이면 검사 생략. · 기본값 0.0",
      "type": "number"
    },
    "exits": {
      "description": "문 하나당 한 항목. 중심 좌표와 유효 폭을 mm로 지정.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "name": {
            "type": "string"
          },
          "width_mm": {
            "type": "number"
          },
          "x_mm": {
            "type": "number"
          },
          "y_mm": {
            "type": "number"
          }
        },
        "required": [
          "x_mm",
          "y_mm",
          "width_mm"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "net_area_m2": {
      "description": "실제 재실 면적. 생략 또는 0이면 경계의 직사각형 면적.",
      "type": "number"
    },
    "occupancy": {
      "default": "business",
      "description": "business, mercantile, assembly_unconcentrated, classroom, residential, storage. · 기본값 \"business\"",
      "type": "string"
    },
    "plate_bounds_mm": {
      "description": "층 바닥 경계 [min_x, min_y, max_x, max_y].",
      "items": {
        "type": "number"
      },
      "maxItems": 4,
      "minItems": 4,
      "type": "array"
    },
    "sprinklered": {
      "default": true,
      "description": "전체 구역 설치 기준. · 기본값 true",
      "type": "boolean"
    },
    "stories": {
      "description": "출구가 담당하는 층수. 기본 1. 2층 이상은 최소 2개 출구와 계단 폭 기준 적용.",
      "type": "integer"
    },
    "travel_distances_m": {
      "description": "입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략. · 기본값 []",
      "items": {
        "type": "number"
      },
      "type": "array"
    }
  },
  "required": [
    "exits",
    "plate_bounds_mm"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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

**beyond · RhinoTerminal**

```txt
저장된 도면 패키지의 SVG·DXF를 파일 해시 목록과 대조. 빈 해시 목록, 누락·변경 파일, 패키지 외부 경로, 파일시스템 링크는 오류. 원본을 찾으면 원본 변경도 검사.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "package_dir": {
      "description": "도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_glb": {
      "description": "원본이 바뀌었는지 비교할 GLB. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 라이브러리에서 원본을 찾을 수 있으면 생략 가능.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "package_dir"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "package_dir": {
      "description": "도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "source_glb": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
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
    "source_geometry": {
      "description": "not_checked이면 파일만 검사했다.",
      "enum": [
        "current",
        "source_file_current",
        "stale",
        "not_checked"
      ],
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

**beyond · RhinoTerminal**

```txt
등록 3DM 또는 삼각형 GLB(정적·비압축, 최대 100 MB·250,000 삼각형)에서 평면·정면·우측면 실루엣을 생성한다. GLB 경로는 관리형에서 프로젝트 상대 경로, 독립 실행에서 절대 경로다. 기본 위쪽 축은 y이고 (X, -Z, Y)로 변환한다. 실물 크기 mm DXF와 축척 SVG를 출력. 세 뷰가 A3에 들어가면 시트 SVG도 생성하며, 시트 없이도 성공 가능.

정면은 좌표계 기준. 실루엣에 단면·내부 가시선·은선은 없으며 축척별 단순화로 작은 윤곽이 달라질 수 있음. 결과는 별도 drawing-runs에 저장하고 등록 자산의 도면은 갱신하지 않음.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "input_units": false,
        "source_glb": false,
        "up_axis": false
      },
      "required": [
        "asset_id"
      ]
    },
    {
      "properties": {
        "asset_id": false
      },
      "required": [
        "source_glb",
        "input_units"
      ]
    }
  ],
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "input_units": {
      "enum": [
        "mm",
        "m"
      ],
      "type": "string"
    },
    "scales": {
      "description": "서로 다른 5~1000 범위의 분모 1~4개. 기본 [50, 100].",
      "items": {
        "type": "integer"
      },
      "type": "array"
    },
    "source_glb": {
      "type": "string"
    },
    "source_references": {
      "items": {
        "additionalProperties": false,
        "properties": {
          "accessed_on": {
            "type": "string"
          },
          "locator": {
            "type": "string"
          },
          "publisher": {
            "type": "string"
          },
          "relationship": {
            "enum": [
              "background_reading",
              "dimensional_reference",
              "assembly_reference",
              "post_generation_reference"
            ],
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
          },
          "used_for": {
            "type": "string"
          }
        },
        "required": [
          "source_id",
          "title",
          "url",
          "publisher",
          "locator",
          "accessed_on",
          "used_for",
          "terms_url",
          "relationship"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "up_axis": {
      "enum": [
        "y",
        "z"
      ],
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "input_units": false,
        "source_glb": false,
        "up_axis": false
      },
      "required": [
        "asset_id"
      ]
    },
    {
      "properties": {
        "asset_id": false
      },
      "required": [
        "source_glb",
        "input_units"
      ]
    }
  ],
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "input_units": {
      "enum": [
        "mm",
        "m"
      ],
      "type": "string"
    },
    "scales": {
      "description": "서로 다른 5~1000 범위의 분모 1~4개. 기본 [50, 100].",
      "items": {
        "type": "integer"
      },
      "type": "array"
    },
    "source_glb": {
      "type": "string"
    },
    "source_references": {
      "items": {
        "additionalProperties": false,
        "properties": {
          "accessed_on": {
            "type": "string"
          },
          "locator": {
            "type": "string"
          },
          "publisher": {
            "type": "string"
          },
          "relationship": {
            "enum": [
              "background_reading",
              "dimensional_reference",
              "assembly_reference",
              "post_generation_reference"
            ],
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
          },
          "used_for": {
            "type": "string"
          }
        },
        "required": [
          "source_id",
          "title",
          "url",
          "publisher",
          "locator",
          "accessed_on",
          "used_for",
          "terms_url",
          "relationship"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "up_axis": {
      "enum": [
        "y",
        "z"
      ],
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "manifest": {
      "additionalProperties": true,
      "type": "object"
    },
    "message": {
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

**beyond · RhinoTerminal**

```txt
등록 자산의 저장 도면 패키지 조회. 도면은 배치 인스턴스 변환을 적용하지 않은 자산 원본 형상의 투영. manifest에서 파일·축척·치수·출처·투영 한계를 확인.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "manifest": {
      "additionalProperties": true,
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "package_dir": {
      "description": "asset_01-audit_drawing tool에 전달.",
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

**beyond · RhinoTerminal**

```txt
모델·2D 자산의 등록 정보와 사용 가능 상태 조회. field_groups에 paths를 지정하면 원본·모델 경로를 확인.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset": {
            "properties": {
              "category": {
                "type": "string"
              },
              "dimensions_mm": {
                "additionalProperties": {
                  "type": "number"
                },
                "type": "object"
              },
              "drawing_status": {
                "type": "string"
              },
              "file_available": {
                "type": "boolean"
              },
              "model_path": {
                "type": "string"
              },
              "model_status": {
                "type": "string"
              },
              "next_tool": {
                "description": "변환이나 갱신이 필요할 때 호출할 도구.",
                "type": "string"
              },
              "product": {
                "type": "string"
              },
              "source_available": {
                "type": "boolean"
              },
              "source_only": {
                "type": "boolean"
              },
              "source_path": {
                "type": "string"
              },
              "spatial": {
                "additionalProperties": true,
                "type": "object"
              },
              "variant": {
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

**beyond · RhinoTerminal**

```txt
모델·2D 자산 목록과 배치 준비 상태 조회. asset_id는 상세 조회와 배치에 사용한다.
next_offset이 있으면 같은 조건으로 다음 페이지를 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "빈 값은 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "limit": {
      "default": 20,
      "description": "기본값 20",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터). · 기본값 0",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "빈 값은 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "limit": {
      "default": 20,
      "description": "기본값 20",
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터). · 기본값 0",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "properties": {
                "asset_id": {
                  "type": "string"
                },
                "category": {
                  "type": "string"
                },
                "dimensions_mm": {
                  "additionalProperties": {
                    "type": "number"
                  },
                  "type": "object"
                },
                "drawing_status": {
                  "type": "string"
                },
                "file_available": {
                  "type": "boolean"
                },
                "model_path": {
                  "type": "string"
                },
                "model_status": {
                  "type": "string"
                },
                "next_tool": {
                  "description": "변환이나 갱신이 필요할 때 호출할 도구.",
                  "type": "string"
                },
                "product": {
                  "type": "string"
                },
                "source_available": {
                  "type": "boolean"
                },
                "source_only": {
                  "type": "boolean"
                },
                "source_path": {
                  "type": "string"
                },
                "spatial": {
                  "additionalProperties": true,
                  "type": "object"
                },
                "variant": {
                  "type": "string"
                }
              },
              "required": [
                "asset_id"
              ],
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
          "next_offset": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
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


### 11. asset_06-place

**beyond · RhinoTerminal**

```txt
모델·2D 자산을 Rhino 문서에 블록으로 배치. 3DM은 원본에 연결되며 정의를 갱신하면 같은 정의를 사용하는 기존 배치에 반영.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준. · 기본값 0",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "균일 배치 축척(0 초과 100 이하). · 기본값 1",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
      "type": "number"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "rotation_degrees": {
      "default": 0,
      "description": "월드 Z축 기준. · 기본값 0",
      "type": "number"
    },
    "scale": {
      "default": 1,
      "description": "균일 배치 축척(0 초과 100 이하). · 기본값 1",
      "type": "number"
    },
    "x": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
      "type": "number"
    },
    "y": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
      "type": "number"
    },
    "z": {
      "default": 0,
      "description": "원본 기준점의 월드 좌표(문서 단위). · 기본값 0",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "affected_existing_instances": {
            "type": "integer"
          },
          "definition_created": {
            "type": "boolean"
          },
          "definition_refreshed": {
            "type": "boolean"
          },
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_applied": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "null이면 변경 적용 여부 미확인."
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "next_tool": {
            "const": "asset_07-prepare",
            "description": "3DM 변환이 필요한 원본의 준비 도구.",
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

**beyond · RhinoTerminal**

```txt
inspect는 원본을 보존하고 미리보기를 만든다. 3DM은 내장 단위를 쓰고 다른 형식은 입력 단위를 지정한다. 새 normalize에는 검토를 제출한다. 이미 끝난 단계는 같은 job_dir로 조회할 수 있다. 첫 verify에서 받은 최종 이미지와 해시를 확인한 뒤 같은 job_dir로 검토를 제출한다. ready면 source_3dm과 job_dir를 등록에 사용한다. status는 저장된 근거만 읽는다. 관리형 경로는 프로젝트 상대 경로, 독립 실행에서는 절대 경로다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "job_dir": false,
        "review": false,
        "stage": {
          "const": "inspect",
          "type": "string"
        }
      },
      "required": [
        "source_file"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": {
          "additionalProperties": false,
          "properties": {
            "inspected_sha256": {
              "type": "string"
            },
            "remove": {
              "items": {
                "additionalProperties": false,
                "properties": {
                  "object_id": {
                    "type": "string"
                  },
                  "reason": {
                    "type": "string"
                  }
                },
                "required": [
                  "object_id",
                  "reason"
                ],
                "type": "object"
              },
              "type": "array"
            },
            "rotation_degrees_xyz": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "translation": {
              "description": "원본 단위",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "inspected_sha256"
          ],
          "type": "object"
        },
        "source_file": false,
        "stage": {
          "const": "normalize",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": {
          "additionalProperties": false,
          "properties": {
            "asset_id": {
              "type": "string"
            },
            "final_sha256": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "final_sha256",
            "name",
            "asset_id"
          ],
          "type": "object"
        },
        "source_file": false,
        "stage": {
          "const": "verify",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": false,
        "source_file": false,
        "stage": {
          "const": "status",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    }
  ],
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "description": "생략 시 미리보기 포함, []는 요약. limit·offset은 parts에만 적용.",
      "items": {
        "enum": [
          "summary",
          "parts",
          "previews",
          "provenance",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "include_ids": {
      "type": "boolean"
    },
    "input_units": {
      "enum": [
        "mm",
        "cm",
        "m",
        "in",
        "ft"
      ],
      "type": "string"
    },
    "job_dir": {
      "type": "string"
    },
    "limit": {
      "description": "1~200, 기본 50",
      "maximum": 200,
      "minimum": 1,
      "type": "integer"
    },
    "offset": {
      "minimum": 0,
      "type": "integer"
    },
    "review": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "inspected_sha256": {
              "type": "string"
            },
            "remove": {
              "items": {
                "additionalProperties": false,
                "properties": {
                  "object_id": {
                    "type": "string"
                  },
                  "reason": {
                    "type": "string"
                  }
                },
                "required": [
                  "object_id",
                  "reason"
                ],
                "type": "object"
              },
              "type": "array"
            },
            "rotation_degrees_xyz": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "translation": {
              "description": "원본 단위",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "inspected_sha256"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "asset_id": {
              "type": "string"
            },
            "final_sha256": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "final_sha256",
            "name",
            "asset_id"
          ],
          "type": "object"
        }
      ]
    },
    "source_file": {
      "type": "string"
    },
    "stage": {
      "enum": [
        "inspect",
        "normalize",
        "verify",
        "status"
      ],
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "stage"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "job_dir": false,
        "review": false,
        "stage": {
          "const": "inspect",
          "type": "string"
        }
      },
      "required": [
        "source_file"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": {
          "additionalProperties": false,
          "properties": {
            "inspected_sha256": {
              "type": "string"
            },
            "remove": {
              "items": {
                "additionalProperties": false,
                "properties": {
                  "object_id": {
                    "type": "string"
                  },
                  "reason": {
                    "type": "string"
                  }
                },
                "required": [
                  "object_id",
                  "reason"
                ],
                "type": "object"
              },
              "type": "array"
            },
            "rotation_degrees_xyz": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "translation": {
              "description": "원본 단위",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "inspected_sha256"
          ],
          "type": "object"
        },
        "source_file": false,
        "stage": {
          "const": "normalize",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": {
          "additionalProperties": false,
          "properties": {
            "asset_id": {
              "type": "string"
            },
            "final_sha256": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "final_sha256",
            "name",
            "asset_id"
          ],
          "type": "object"
        },
        "source_file": false,
        "stage": {
          "const": "verify",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    },
    {
      "properties": {
        "input_units": false,
        "review": false,
        "source_file": false,
        "stage": {
          "const": "status",
          "type": "string"
        }
      },
      "required": [
        "job_dir"
      ]
    }
  ],
  "properties": {
    "field_groups": {
      "description": "생략 시 미리보기 포함, []는 요약. limit·offset은 parts에만 적용.",
      "items": {
        "enum": [
          "summary",
          "parts",
          "previews",
          "provenance",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "include_ids": {
      "type": "boolean"
    },
    "input_units": {
      "enum": [
        "mm",
        "cm",
        "m",
        "in",
        "ft"
      ],
      "type": "string"
    },
    "job_dir": {
      "type": "string"
    },
    "limit": {
      "description": "1~200, 기본 50",
      "maximum": 200,
      "minimum": 1,
      "type": "integer"
    },
    "offset": {
      "minimum": 0,
      "type": "integer"
    },
    "review": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "inspected_sha256": {
              "type": "string"
            },
            "remove": {
              "items": {
                "additionalProperties": false,
                "properties": {
                  "object_id": {
                    "type": "string"
                  },
                  "reason": {
                    "type": "string"
                  }
                },
                "required": [
                  "object_id",
                  "reason"
                ],
                "type": "object"
              },
              "type": "array"
            },
            "rotation_degrees_xyz": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "translation": {
              "description": "원본 단위",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "inspected_sha256"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "asset_id": {
              "type": "string"
            },
            "final_sha256": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "vision_reviewed": {
              "const": true,
              "type": "boolean"
            }
          },
          "required": [
            "vision_reviewed",
            "final_sha256",
            "name",
            "asset_id"
          ],
          "type": "object"
        }
      ]
    },
    "source_file": {
      "type": "string"
    },
    "stage": {
      "enum": [
        "inspect",
        "normalize",
        "verify",
        "status"
      ],
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
    "next_offset": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ]
    },
    "next_stage": {
      "anyOf": [
        {
          "const": "verify",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "verified 상태에서 verify를 호출할 때는 최종 이미지 검토를 제출. ready면 source_3dm으로 등록."
    },
    "parts": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "previews": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "provenance": {
      "additionalProperties": true,
      "type": "object"
    },
    "requires_reconciliation": {
      "type": "boolean"
    },
    "review_targets": {
      "properties": {
        "final_sha256": {
          "type": "string"
        },
        "inspected_sha256": {
          "type": "string"
        },
        "normalized_sha256": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "source_3dm": {
      "description": "검토를 마친 최종 3DM. 검토한 name·asset_id와 함께 asset_09-register tool에 전달.",
      "type": "string"
    },
    "state": {
      "description": "ready는 해당 해시의 이미지 검토가 기록됐다는 뜻이다.",
      "enum": [
        "new",
        "running",
        "inspected",
        "normalized",
        "verified",
        "ready",
        "failed",
        "unconfirmed"
      ],
      "type": "string"
    },
    "status": {
      "description": "passed는 단계 검사 통과. 등록에는 state가 ready일 때의 source_3dm을 쓴다.",
      "enum": [
        "pending",
        "passed",
        "error"
      ],
      "type": "string"
    },
    "summary": {
      "properties": {
        "dimensions_mm": {
          "additionalProperties": {
            "type": "number"
          },
          "type": "object"
        },
        "limitations": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "object_count": {
          "type": "integer"
        },
        "units": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "total": {
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>


### 13. asset_08-refresh

**beyond · RhinoTerminal**

```txt
편집·저장한 등록 3DM을 다시 측정해 평면·입면 도면을 새 리비전으로 발행. 원본 경로와 이전 도면은 보존. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외.

열린 Rhino 문서의 연결 블록 갱신·저장은 별도. 공유 정의를 갱신하면 기존 인스턴스에 반영되며 배치 당시 메타데이터는 유지.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "live_index_refreshed": {
      "description": "게시됐지만 인덱스 갱신에 실패하면 false. 다시 게시하지 말고 재연결한다.",
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_path": {
      "type": "string"
    },
    "package_dir": {
      "type": "string"
    },
    "registration_applied": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ]
    },
    "requires_reconciliation": {
      "description": "변경이 미확정이면 모델과 라이브러리를 확인한 뒤 재시도한다.",
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

**beyond · RhinoTerminal**

```txt
검토한 3DM을 모델 라이브러리에 등록하고 치수·평면·입면 실루엣 도면을 생성. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외. 준비를 마쳤어도 파생 메시가 250,000 삼각형을 넘으면 등록 실패. 등록 결과는 asset_04-get tool에서 확인.
```

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
      "description": "기본값 \"other\"",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "name": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.",
      "type": "string"
    },
    "preparation_job": {
      "description": "완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "replace_existing": {
      "description": "true일 때만 같은 ID의 기존 자산 교체.",
      "type": "boolean"
    },
    "source_3dm": {
      "description": "관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.",
      "type": "string"
    },
    "source_url": {
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
      ]
    }
  },
  "required": [
    "connection_id",
    "asset_id",
    "name",
    "source_3dm"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "기본값 \"other\"",
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "name": {
      "description": "preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.",
      "type": "string"
    },
    "preparation_job": {
      "description": "완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.",
      "type": "string"
    },
    "replace_existing": {
      "description": "true일 때만 같은 ID의 기존 자산 교체.",
      "type": "boolean"
    },
    "source_3dm": {
      "description": "관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.",
      "type": "string"
    },
    "source_url": {
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
      ]
    }
  },
  "required": [
    "asset_id",
    "name",
    "source_3dm"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "linked_instances_may_update": {
      "description": "기존 원본을 교체하면 해당 원본에 연결된 인스턴스에 영향 가능.",
      "type": "boolean"
    },
    "live_index_refreshed": {
      "description": "게시됐지만 인덱스 갱신에 실패하면 false. 다시 게시하지 말고 재연결한다.",
      "type": "boolean"
    },
    "message": {
      "type": "string"
    },
    "model_path": {
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
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "registration_applied": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ]
    },
    "requires_reconciliation": {
      "description": "게시 결과가 불명확하면 null과 requires_reconciliation 반환. 상태 확인 없이 재시도 금지.",
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

**beyond · RhinoTerminal**

```txt
모델·2D 요소 아카이브 검색. 후보가 limit에서 잘리면 검색어나 유형을 좁혀 다시 조회. 원본만 있는 자산은 변환이 필요할 수 있으며 asset_id를 asset_04-get tool에 전달해 상세 정보·경로를 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "drawing_ready": {
      "type": "boolean"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "kind": {
      "default": "all",
      "description": "all, element, model. · 기본값 \"all\"",
      "enum": [
        "all",
        "model",
        "element"
      ],
      "type": "string"
    },
    "limit": {
      "default": 20,
      "description": "1..100으로 보정. · 기본값 20",
      "type": "integer"
    },
    "query": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "drawing_ready": {
      "type": "boolean"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "kind": {
      "default": "all",
      "description": "all, element, model. · 기본값 \"all\"",
      "enum": [
        "all",
        "model",
        "element"
      ],
      "type": "string"
    },
    "limit": {
      "default": 20,
      "description": "1..100으로 보정. · 기본값 20",
      "type": "integer"
    },
    "query": {
      "description": "이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "assets": {
      "items": {
        "properties": {
          "asset_id": {
            "type": "string"
          },
          "available": {
            "type": "boolean"
          },
          "dimensions_mm": {
            "additionalProperties": {
              "type": "number"
            },
            "type": "object"
          },
          "drawing_ready": {
            "type": "boolean"
          },
          "drawing_status": {
            "type": "string"
          },
          "kind": {
            "enum": [
              "model",
              "element"
            ],
            "type": "string"
          },
          "model_status": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "source_available": {
            "type": "boolean"
          },
          "source_only": {
            "type": "boolean"
          }
        },
        "required": [
          "asset_id"
        ],
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

**beyond · RhinoTerminal**

```txt
모델·2D 자산을 검색어·분류·최대 치수로 검색. 단어가 하나라도 일치하면 포함하고 일치 단어가 많은 순으로 반환. 치수 필터는 등록 치수를 비교하며 해당 치수가 없는 자산도 포함할 수 있음. asset_id를 asset_04-get tool에 전달해 상세 조회.
next_offset이 있으면 같은 조건으로 다음 페이지를 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "limit": {
      "default": 10,
      "description": "페이지당 1~100개. · 기본값 10",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터). · 기본값 0",
      "type": "integer"
    },
    "query": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "dimensions",
          "source",
          "paths",
          "drawing",
          "metadata",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "limit": {
      "default": 10,
      "description": "페이지당 1~100개. · 기본값 10",
      "type": "integer"
    },
    "max_depth_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "max_height_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "max_width_mm": {
      "default": 0,
      "description": "양수일 때만 필터 적용. · 기본값 0",
      "type": "number"
    },
    "offset": {
      "default": 0,
      "description": "페이지의 시작 위치(0부터). · 기본값 0",
      "type": "integer"
    },
    "query": {
      "description": "이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "properties": {
                "asset_id": {
                  "type": "string"
                },
                "category": {
                  "type": "string"
                },
                "dimensions_mm": {
                  "additionalProperties": {
                    "type": "number"
                  },
                  "type": "object"
                },
                "drawing_status": {
                  "type": "string"
                },
                "file_available": {
                  "type": "boolean"
                },
                "model_path": {
                  "type": "string"
                },
                "model_status": {
                  "type": "string"
                },
                "next_tool": {
                  "description": "변환이나 갱신이 필요할 때 호출할 도구.",
                  "type": "string"
                },
                "product": {
                  "type": "string"
                },
                "source_available": {
                  "type": "boolean"
                },
                "source_only": {
                  "type": "boolean"
                },
                "source_path": {
                  "type": "string"
                },
                "spatial": {
                  "additionalProperties": true,
                  "type": "object"
                },
                "variant": {
                  "type": "string"
                }
              },
              "required": [
                "asset_id"
              ],
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
          "next_offset": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
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


### 17. capture_01-conditioning_pass

**beyond · RhinoTerminal**

```txt
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장한다. 뷰가 변경되고 복원이 일부만 적용될 수 있다. 출력 폴더를 재사용하면 기존 파일을 덮어쓰거나 이전 프레임이 남을 수 있다. PNG와 대상 가시성은 파일에서 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "chunk": {
      "default": 16,
      "description": "청크당 프레임 수. 양의 정수 · 기본값 16",
      "type": "integer"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "edge_mode": {
      "description": "기본 Technical\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "fps": {
      "default": 16,
      "description": "초당 프레임 수. 양의 정수 · 기본값 16",
      "type": "integer"
    },
    "height": {
      "default": 480,
      "description": "양의 짝수 픽셀 · 기본값 480",
      "type": "integer"
    },
    "invert_depth": {
      "description": "false이면 가까울수록 밝게 표현.",
      "type": "boolean"
    },
    "out_dir": {
      "description": "선택한 Plan의 산출물 폴더 기준 상대 경로. 기본 conditioning.",
      "type": "string"
    },
    "passes": {
      "default": "rgb,edge,depth",
      "description": "쉼표로 구분한 rgb, edge, depth. · 기본값 \"rgb,edge,depth\"",
      "type": "string"
    },
    "rgb_mode": {
      "description": "기본 Rendered\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "shot": {
      "description": "카메라 경로 JSON 문자열. 좌표는 문서 단위, lens는 mm, frames 기본 81.\ntype=orbit: center, radius, height, 선택 start_deg·end_deg·lens·target_height.\ntype=track: cam0, cam1, target0, target1, 선택 lens.\ntype=keyframes: keyframes 배열의 각 항목에 camera, target, 선택 lens.",
      "type": "string"
    },
    "width": {
      "default": 832,
      "description": "양의 짝수 픽셀 · 기본값 832",
      "type": "integer"
    }
  },
  "required": [
    "connection_id",
    "shot"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "chunk": {
      "default": 16,
      "description": "청크당 프레임 수. 양의 정수 · 기본값 16",
      "type": "integer"
    },
    "edge_mode": {
      "description": "기본 Technical\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "fps": {
      "default": 16,
      "description": "초당 프레임 수. 양의 정수 · 기본값 16",
      "type": "integer"
    },
    "height": {
      "default": 480,
      "description": "양의 짝수 픽셀 · 기본값 480",
      "type": "integer"
    },
    "invert_depth": {
      "description": "false이면 가까울수록 밝게 표현.",
      "type": "boolean"
    },
    "out_dir": {
      "description": "선택한 Plan의 산출물 폴더 기준 상대 경로. 기본 conditioning.",
      "type": "string"
    },
    "passes": {
      "default": "rgb,edge,depth",
      "description": "쉼표로 구분한 rgb, edge, depth. · 기본값 \"rgb,edge,depth\"",
      "type": "string"
    },
    "rgb_mode": {
      "description": "기본 Rendered\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "shot": {
      "description": "카메라 경로 JSON 문자열. 좌표는 문서 단위, lens는 mm, frames 기본 81.\ntype=orbit: center, radius, height, 선택 start_deg·end_deg·lens·target_height.\ntype=track: cam0, cam1, target0, target1, 선택 lens.\ntype=keyframes: keyframes 배열의 각 항목에 camera, target, 선택 lens.",
      "type": "string"
    },
    "width": {
      "default": 832,
      "description": "양의 짝수 픽셀 · 기본값 832",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "camera_json": {
            "description": "촬영 성공 범위와 무관하게 계획한 전체 경로를 기록한 파일.",
            "type": "string"
          },
          "document": {
            "additionalProperties": true,
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
          "out_dir": {
            "description": "패스별 PNG와 doc.json, camera.json, zrange.csv, summary.json 저장 위치.",
            "type": "string"
          },
          "status": {
            "description": "executed는 전체 청크 완료. partial은 일부 청크만 완료.",
            "enum": [
              "executed",
              "partial",
              "error"
            ],
            "type": "string"
          },
          "videos": {
            "additionalProperties": false,
            "properties": {
              "depth": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "edge": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "rgb": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
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

**beyond · RhinoTerminal**

```txt
작업 화면을 유지하며 여러 시점과 객체 범위를 타일 PNG로 비교한다. 범위는 문서의 표시 상태 기준이며 픽셀 가시성은 이미지에서 확인한다.
```

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
      "description": "1..뷰 개수. 생략 시 자동 격자.",
      "maximum": 16,
      "minimum": 1
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "default": 480,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 480",
      "maximum": 2048,
      "minimum": 128,
      "type": "integer"
    },
    "model_view_id": {
      "description": "활성화 없이 사용할 모델 뷰포트 GUID. Layout·Detail에서도 지정 가능.",
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
      "description": "모든 타일의 최상위 객체 GUID 1..4096개, 블록 인스턴스 제외. 타일별 object_ids와 동시 지정 불가.",
      "maxItems": 4096,
      "minItems": 1,
      "uniqueItems": true
    },
    "views": {
      "description": "타일 1..16개. 타일별 범위가 비어 있으면 공통 범위 또는 문서 표시 상태를 사용.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "direction": {
            "description": "기본 current",
            "enum": [
              "current",
              "top",
              "bottom",
              "front",
              "back",
              "left",
              "right",
              "iso_ne",
              "iso_nw",
              "iso_se",
              "iso_sw",
              "below_ne",
              "below_nw",
              "below_se",
              "below_sw"
            ],
            "type": "string"
          },
          "display_mode": {
            "description": "inspect_03-get_document_context tool의 display_modes[].id",
            "maxLength": 512,
            "type": "string"
          },
          "frame_objects": {
            "description": "current에서 범위 객체에 맞게 확대. object_ids 필요.",
            "type": "boolean"
          },
          "label": {
            "description": "120자 이하",
            "maxLength": 120,
            "type": "string"
          },
          "object_ids": {
            "description": "최상위 객체 GUID 1..512개, 블록 인스턴스 제외",
            "items": {
              "type": "string"
            },
            "maxItems": 512,
            "type": "array",
            "uniqueItems": true
          }
        },
        "type": "object"
      },
      "maxItems": 16,
      "minItems": 1,
      "type": "array"
    },
    "width": {
      "default": 640,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 640",
      "maximum": 2048,
      "minimum": 128,
      "type": "integer"
    }
  },
  "required": [
    "connection_id",
    "views"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "1..뷰 개수. 생략 시 자동 격자.",
      "maximum": 16,
      "minimum": 1
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "height": {
      "default": 480,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 480",
      "maximum": 2048,
      "minimum": 128,
      "type": "integer"
    },
    "model_view_id": {
      "description": "활성화 없이 사용할 모델 뷰포트 GUID. Layout·Detail에서도 지정 가능.",
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
      "description": "모든 타일의 최상위 객체 GUID 1..4096개, 블록 인스턴스 제외. 타일별 object_ids와 동시 지정 불가.",
      "maxItems": 4096,
      "minItems": 1,
      "uniqueItems": true
    },
    "views": {
      "description": "타일 1..16개. 타일별 범위가 비어 있으면 공통 범위 또는 문서 표시 상태를 사용.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "direction": {
            "description": "기본 current",
            "enum": [
              "current",
              "top",
              "bottom",
              "front",
              "back",
              "left",
              "right",
              "iso_ne",
              "iso_nw",
              "iso_se",
              "iso_sw",
              "below_ne",
              "below_nw",
              "below_se",
              "below_sw"
            ],
            "type": "string"
          },
          "display_mode": {
            "description": "inspect_03-get_document_context tool의 display_modes[].id",
            "maxLength": 512,
            "type": "string"
          },
          "frame_objects": {
            "description": "current에서 범위 객체에 맞게 확대. object_ids 필요.",
            "type": "boolean"
          },
          "label": {
            "description": "120자 이하",
            "maxLength": 120,
            "type": "string"
          },
          "object_ids": {
            "description": "최상위 객체 GUID 1..512개, 블록 인스턴스 제외",
            "items": {
              "type": "string"
            },
            "maxItems": 512,
            "type": "array",
            "uniqueItems": true
          }
        },
        "type": "object"
      },
      "maxItems": 16,
      "minItems": 1,
      "type": "array"
    },
    "width": {
      "default": 640,
      "description": "타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 640",
      "maximum": 2048,
      "minimum": 128,
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
      "description": "저장에 실패해도 PNG는 전달될 수 있다.\npath는 프로젝트 상대 경로. connection 파일은 연결 해제 때 정리된다.",
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "error_code": {
          "type": "string"
        },
        "lifetime": {
          "enum": [
            "plan",
            "connection"
          ],
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "path": {
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "enum": [
            "saved",
            "error"
          ],
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "tiles": {
      "description": "실패한 타일도 포함.",
      "items": {
        "properties": {
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
          "error_code": {
            "type": "string"
          },
          "index": {
            "description": "0부터 시작.",
            "type": "integer"
          },
          "message": {
            "type": "string"
          },
          "scope": {
            "properties": {
              "complete": {
                "type": "boolean"
              },
              "eligible_count": {
                "type": "integer"
              },
              "excluded_requested_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "type": "object"
          },
          "status": {
            "enum": [
              "success",
              "error"
            ],
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

**beyond · RhinoTerminal**

```txt
현재 모델 뷰를 PNG로 캡처한다. 대상을 지정하면 실제 선택과 카메라가 바뀌며 isolate와 display_mode도 작업 화면에 적용된다. 고정 크기는 width·height와 scale_percent=100을 함께 지정한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "default": 1,
      "description": "레이블 확장 깊이 1..8. · 기본값 1",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "display_mode": {
      "description": "inspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    },
    "include_usage": {
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "isolate": {
      "description": "target_ids가 필요하며 확대 전에 격리.",
      "type": "boolean"
    },
    "labels": {
      "description": "주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100. · 기본값 75",
      "maximum": 100,
      "minimum": 1,
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
      "description": "선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처."
    },
    "target_kind": {
      "description": "기본 object. 다른 종류에는 target_ids 필요. block에는 배치 객체 ID 사용.",
      "enum": [
        "object",
        "group",
        "block",
        "holon"
      ],
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
      "description": "128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "default": 1,
      "description": "레이블 확장 깊이 1..8. · 기본값 1",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "display_mode": {
      "description": "inspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    },
    "include_usage": {
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "isolate": {
      "description": "target_ids가 필요하며 확대 전에 격리.",
      "type": "boolean"
    },
    "labels": {
      "description": "주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100. · 기본값 75",
      "maximum": 100,
      "minimum": 1,
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
      "description": "선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처."
    },
    "target_kind": {
      "description": "기본 object. 다른 종류에는 target_ids 필요. block에는 배치 객체 ID 사용.",
      "enum": [
        "object",
        "group",
        "block",
        "holon"
      ],
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
      "description": "128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
              "description": "좌표와 프러스텀 경계는 문서 단위.",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "camera_target": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "frustum": {
              "description": "left, right, bottom, top, near, far",
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
              "description": "좌표와 프러스텀 경계는 문서 단위.",
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "camera_target": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "frustum": {
              "description": "left, right, bottom, top, near, far",
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
          "description": "대상 합집합 경계. 좌표는 문서 단위.",
          "properties": {
            "max": {
              "items": {
                "type": "number"
              },
              "maxItems": 3,
              "minItems": 3,
              "type": "array"
            },
            "min": {
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
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        },
        "zoom_extents_selected": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "type": "object"
    },
    "image_file": {
      "description": "저장과 PNG 전달은 별개로 확인.\npath는 프로젝트 상대 경로. connection 파일은 연결 해제 때 정리된다.",
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "error_code": {
          "type": "string"
        },
        "lifetime": {
          "enum": [
            "plan",
            "connection"
          ],
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "path": {
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "enum": [
            "saved",
            "error"
          ],
          "type": "string"
        }
      },
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "mutation_applied": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ],
      "description": "null이면 뷰 변경 적용을 확인하지 못한 상태."
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
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        },
        "isolated": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "description": "Unisolate로 가시성을 복구. 카메라와 선택은 별도로 확인."
        },
        "selection_changed": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        },
        "zoom_method": {
          "description": "bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.",
          "enum": [
            "selected",
            "bounding_box"
          ],
          "type": "string"
        },
        "zoom_selected": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "description": "선택 확대 또는 대체 경계 확대를 완료하면 true."
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

**beyond · RhinoTerminal**

```txt
Named View는 저장된 카메라로 캡처한다. Layout은 용지와 Detail의 인쇄 설정을 사용하므로 픽셀 크기·표시 모드·Detail 레이블을 생략한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "default": 1,
      "description": "레이블 깊이 1..8. · 기본값 1",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "display_mode": {
      "description": "Named View 전용, 기본 Shaded\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "Named View 전용 128..2048픽셀. width와 scale_percent=100을 함께 지정.",
      "maximum": 2048,
      "minimum": 128
    },
    "include_usage": {
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "labels": {
      "description": "최대 200개. 주변 레이블과 겹칠 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다. · 기본값 75",
      "maximum": 100,
      "minimum": 1,
      "type": "integer"
    },
    "target": {
      "description": "기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.",
      "type": "string"
    },
    "target_kind": {
      "enum": [
        "named_view",
        "layout"
      ],
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
      "description": "Named View 전용 128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    }
  },
  "required": [
    "connection_id",
    "target",
    "target_kind"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "default": 1,
      "description": "레이블 깊이 1..8. · 기본값 1",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "display_mode": {
      "description": "Named View 전용, 기본 Shaded\ninspect_03-get_document_context tool의 display_modes[].id",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "Named View 전용 128..2048픽셀. width와 scale_percent=100을 함께 지정.",
      "maximum": 2048,
      "minimum": 128
    },
    "include_usage": {
      "description": "이미지 크기와 픽셀 기준 토큰 추정치 포함.",
      "type": "boolean"
    },
    "labels": {
      "description": "최대 200개. 주변 레이블과 겹칠 수 있다.",
      "type": "boolean"
    },
    "scale_percent": {
      "default": 75,
      "description": "1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다. · 기본값 75",
      "maximum": 100,
      "minimum": 1,
      "type": "integer"
    },
    "target": {
      "description": "기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.",
      "type": "string"
    },
    "target_kind": {
      "enum": [
        "named_view",
        "layout"
      ],
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
      "description": "Named View 전용 128..2048픽셀",
      "maximum": 2048,
      "minimum": 128
    }
  },
  "required": [
    "target",
    "target_kind"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "image_file": {
      "description": "path는 프로젝트 상대 경로. connection 파일은 연결 해제 때 정리된다.",
      "properties": {
        "bytes": {
          "type": "integer"
        },
        "error_code": {
          "type": "string"
        },
        "lifetime": {
          "enum": [
            "plan",
            "connection"
          ],
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "path": {
          "type": "string"
        },
        "sha256": {
          "type": "string"
        },
        "status": {
          "enum": [
            "saved",
            "error"
          ],
          "type": "string"
        }
      },
      "type": "object"
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


### 21. capture_05-manipulate_view

**beyond · RhinoTerminal**

```txt
활성 원근 모델 뷰를 회전하거나 확대한다. 결과는 capture_03-current_view tool에 대상 없이 호출해 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "factor": false,
        "operation": {
          "const": "rotate",
          "type": "string"
        }
      },
      "required": [
        "mode"
      ]
    },
    {
      "properties": {
        "mode": false,
        "operation": {
          "const": "zoom",
          "type": "string"
        },
        "pitch_deg": false,
        "yaw_deg": false
      },
      "required": [
        "factor"
      ]
    }
  ],
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "주면 현재 문서의 모델 경로와 일치해야 한다.",
      "type": "string"
    },
    "expected_viewport_id": {
      "description": "주면 현재 활성 뷰포트 ID와 일치해야 한다.",
      "type": "string"
    },
    "factor": {
      "description": "0보다 큰 유한 배율. 2는 2배 확대, 0.5는 절반으로 축소.",
      "exclusiveMinimum": 0,
      "type": "number"
    },
    "mode": {
      "description": "look은 카메라 위치 고정. orbit은 타깃과 카메라 거리 고정.",
      "enum": [
        "look",
        "orbit"
      ],
      "type": "string"
    },
    "operation": {
      "enum": [
        "rotate",
        "zoom"
      ],
      "type": "string"
    },
    "pitch_deg": {
      "description": "yaw_deg 적용 후 상대 상하 회전(도). 양수는 위, 기본 0.",
      "type": "number"
    },
    "yaw_deg": {
      "description": "상대 좌우 회전(도). 양수는 오른쪽, 기본 0. 두 각도 중 하나는 0이 아니어야 하며 수직 회전은 거부.",
      "type": "number"
    }
  },
  "required": [
    "connection_id",
    "operation"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "factor": false,
        "operation": {
          "const": "rotate",
          "type": "string"
        }
      },
      "required": [
        "mode"
      ]
    },
    {
      "properties": {
        "mode": false,
        "operation": {
          "const": "zoom",
          "type": "string"
        },
        "pitch_deg": false,
        "yaw_deg": false
      },
      "required": [
        "factor"
      ]
    }
  ],
  "properties": {
    "expected_model_path": {
      "description": "주면 현재 문서의 모델 경로와 일치해야 한다.",
      "type": "string"
    },
    "expected_viewport_id": {
      "description": "주면 현재 활성 뷰포트 ID와 일치해야 한다.",
      "type": "string"
    },
    "factor": {
      "description": "0보다 큰 유한 배율. 2는 2배 확대, 0.5는 절반으로 축소.",
      "exclusiveMinimum": 0,
      "type": "number"
    },
    "mode": {
      "description": "look은 카메라 위치 고정. orbit은 타깃과 카메라 거리 고정.",
      "enum": [
        "look",
        "orbit"
      ],
      "type": "string"
    },
    "operation": {
      "enum": [
        "rotate",
        "zoom"
      ],
      "type": "string"
    },
    "pitch_deg": {
      "description": "yaw_deg 적용 후 상대 상하 회전(도). 양수는 위, 기본 0.",
      "type": "number"
    },
    "yaw_deg": {
      "description": "상대 좌우 회전(도). 양수는 오른쪽, 기본 0. 두 각도 중 하나는 0이 아니어야 하며 수직 회전은 거부.",
      "type": "number"
    }
  },
  "required": [
    "operation"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "camera_location": {
      "items": {
        "type": "number"
      },
      "maxItems": 3,
      "minItems": 3,
      "type": "array"
    },
    "camera_target": {
      "items": {
        "type": "number"
      },
      "maxItems": 3,
      "minItems": 3,
      "type": "array"
    },
    "error_code": {
      "type": "string"
    },
    "mutation_applied": {
      "anyOf": [
        {
          "type": "boolean"
        },
        {
          "type": "null"
        }
      ]
    },
    "requires_reconciliation": {
      "type": "boolean"
    },
    "status": {
      "enum": [
        "success",
        "error"
      ],
      "type": "string"
    },
    "viewport_id": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "type": "object"
}
```

</details>


### 22. connect_01-list_up

**beyond**

```txt
열린 Rhino 문서와 연결 상태를 조회한다. available이면 host_id와 model_path로 connect_02-session tool에 연결을 요청한다. ready이면 connection_id로 바로 작업한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {},
  "type": "object"
}
```

</details>

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "targets": {
      "items": {
        "properties": {
          "connection_id": {
            "type": "string"
          },
          "host_id": {
            "type": "string"
          },
          "model_path": {
            "type": "string"
          },
          "reason": {
            "type": "string"
          },
          "state": {
            "description": "recovering·unconfirmed이면 이전 실행 결과부터 확인한다.",
            "type": "string"
          }
        },
        "required": [
          "state"
        ],
        "type": "object"
      },
      "type": "array"
    }
  },
  "required": [
    "targets"
  ],
  "type": "object"
}
```

</details>


### 23. connect_02-session

**beyond**

```txt
connect_01-list_up tool에서 고른 문서의 host_id와 model_path로 연결한다. 같은 문서에 이미 연결되어 있으면 기존 connection_id를 반환한다.
```

<details><summary>beyond 입력 스키마</summary>

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

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "connection_id": {
      "type": "string"
    },
    "reason": {
      "type": "string"
    },
    "state": {
      "enum": [
        "ready",
        "recovering",
        "unconfirmed"
      ],
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "state"
  ],
  "type": "object"
}
```

</details>


### 24. connect_03-start_session

**beyond**

```txt
저장된 .3dm을 새 Rhino 창에서 연다. 시작을 기다리는 중이면 같은 경로와 request_id로 조회한다. 독립 실행이 거부되면 Rhino에서 파일을 열고 almondconnect를 실행한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "model_path": {
      "description": "로컬 .3dm 파일의 절대 경로.",
      "type": "string"
    },
    "request_id": {
      "description": "새 창을 열 때마다 정하는 1~128자 고유 문자열.",
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

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "connection_id": {
      "type": "string"
    },
    "reason": {
      "type": "string"
    },
    "state": {
      "enum": [
        "ready",
        "recovering",
        "unconfirmed"
      ],
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "state"
  ],
  "type": "object"
}
```

</details>


### 25. connect_04-disconnect

**beyond**

```txt
연결 슬롯을 해제하고 Rhino 문서는 열어 둔다. 실행 중인 호출이 끝나야 해제할 수 있다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "reason": {
      "description": "연결은 해제됐지만 내부 정리 중 오류가 생긴 경우.",
      "type": "string"
    },
    "released": {
      "const": true,
      "type": "boolean"
    }
  },
  "required": [
    "released"
  ],
  "type": "object"
}
```

</details>


### 26. connect_05-close_session

**beyond**

```txt
Rhino 문서를 저장한 뒤 해당 Rhino 창을 닫는다. 같은 connection_id와 request_id로 다시 호출하면 이전 결과를 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request_id": {
      "description": "종료 요청마다 새로 정하는 1~128자 문자열.",
      "maxLength": 128,
      "minLength": 1,
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "request_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond 출력 스키마</summary>

```json
{
  "properties": {
    "reason": {
      "type": "string"
    },
    "save_request_id": {
      "description": "저장 결과가 불확실할 때 script_03-get_execution tool에 전달할 request_id.",
      "type": "string"
    },
    "status": {
      "description": "completed이면 저장, Rhino 종료, 연결 해제가 모두 끝났다.",
      "enum": [
        "completed",
        "closing",
        "rejected",
        "save_failed",
        "unconfirmed"
      ],
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "type": "object"
}
```

</details>


### 27. context_01-get_policy

**beyond · RhinoTerminal**

```txt
Rhino 기술 자료를 조회한다. `basic`(기본값)은 공통 도구명과 자료 목록, `metadata`는 객체 메타데이터 키 사전, `rhino_scripting`은 스크립팅 문서, `rhinocode`는 실행 지침이다.
```

<details><summary>beyond · RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "policy": {
      "enum": [
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "anyOf": [
    {
      "properties": {
        "available_policies": {
          "additionalProperties": false,
          "properties": {
            "basic": {
              "type": "string"
            },
            "metadata": {
              "type": "string"
            },
            "rhino_scripting": {
              "type": "string"
            },
            "rhinocode": {
              "type": "string"
            }
          },
          "required": [
            "basic",
            "metadata",
            "rhino_scripting",
            "rhinocode"
          ],
          "type": "object"
        },
        "guide_version": {
          "type": "string"
        },
        "selected_policy": {
          "const": "basic",
          "type": "string"
        },
        "tools": {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      },
      "required": [
        "guide_version",
        "selected_policy",
        "available_policies",
        "tools"
      ],
      "type": "object"
    },
    {
      "properties": {
        "guide_version": {
          "type": "string"
        },
        "policy": {
          "additionalProperties": true,
          "type": "object"
        },
        "selected_policy": {
          "const": "metadata",
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
            "required": [
              "path",
              "sha256"
            ],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "guide_version",
        "selected_policy",
        "policy",
        "source_refs"
      ],
      "type": "object"
    },
    {
      "properties": {
        "guide_version": {
          "type": "string"
        },
        "scripting_skill": {
          "properties": {
            "sources": {
              "items": {
                "properties": {
                  "path": {
                    "type": "string"
                  },
                  "sha256": {
                    "type": "string"
                  },
                  "text": {
                    "type": "string"
                  }
                },
                "required": [
                  "path",
                  "sha256",
                  "text"
                ],
                "type": "object"
              },
              "type": "array"
            }
          },
          "required": [
            "sources"
          ],
          "type": "object"
        },
        "selected_policy": {
          "const": "rhino_scripting",
          "type": "string"
        }
      },
      "required": [
        "guide_version",
        "selected_policy",
        "scripting_skill"
      ],
      "type": "object"
    },
    {
      "properties": {
        "guide_version": {
          "type": "string"
        },
        "selected_policy": {
          "const": "rhinocode",
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
            "required": [
              "path",
              "sha256"
            ],
            "type": "object"
          },
          "type": "array"
        },
        "text": {
          "type": "string"
        }
      },
      "required": [
        "guide_version",
        "selected_policy",
        "text",
        "source_refs"
      ],
      "type": "object"
    }
  ],
  "properties": {
    "available_policies": {
      "additionalProperties": false,
      "properties": {
        "basic": {
          "type": "string"
        },
        "metadata": {
          "type": "string"
        },
        "rhino_scripting": {
          "type": "string"
        },
        "rhinocode": {
          "type": "string"
        }
      },
      "required": [
        "basic",
        "metadata",
        "rhino_scripting",
        "rhinocode"
      ],
      "type": "object"
    },
    "guide_version": {
      "type": "string"
    },
    "policy": {
      "additionalProperties": true,
      "type": "object"
    },
    "scripting_skill": {
      "properties": {
        "sources": {
          "items": {
            "properties": {
              "path": {
                "type": "string"
              },
              "sha256": {
                "type": "string"
              },
              "text": {
                "type": "string"
              }
            },
            "required": [
              "path",
              "sha256",
              "text"
            ],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "sources"
      ],
      "type": "object"
    },
    "selected_policy": {
      "enum": [
        "basic",
        "metadata",
        "rhino_scripting",
        "rhinocode"
      ],
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
        "required": [
          "path",
          "sha256"
        ],
        "type": "object"
      },
      "type": "array"
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
  "required": [
    "guide_version",
    "selected_policy"
  ],
  "type": "object"
}
```

</details>


### 28. context_04-get_project_info

**beyond · RhinoTerminal**

```txt
연결한 문서와 프로젝트를 조회한다. 기본 조회에는 레이어 트리, Named View, Layout, 작업 경로가 포함된다. sections로 일부만 고를 수 있고 runtime은 요청할 때만 읽는다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "files_limit": {
      "description": "등록 파일만 페이지로 읽는다. 기본 50개, 범위 1~500. offset에 읽은 개수를 더해 total까지 조회한다.",
      "maximum": 500,
      "minimum": 1,
      "type": "integer"
    },
    "files_offset": {
      "minimum": 0,
      "type": "integer"
    },
    "include_ids": {
      "description": "Plan·Step ID, 문서 실행 번호와 RhinoCode pipe ID도 조회한다.",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "project",
              "document",
              "layer_tree",
              "named_views",
              "layouts",
              "locations",
              "runtime"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "files_limit": {
      "description": "등록 파일만 페이지로 읽는다. 기본 50개, 범위 1~500. offset에 읽은 개수를 더해 total까지 조회한다.",
      "maximum": 500,
      "minimum": 1,
      "type": "integer"
    },
    "files_offset": {
      "minimum": 0,
      "type": "integer"
    },
    "include_ids": {
      "description": "Plan·Step ID, 문서 실행 번호와 RhinoCode pipe ID도 조회한다.",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "project",
              "document",
              "layer_tree",
              "named_views",
              "layouts",
              "locations",
              "runtime"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "anyOf": [
    {
      "properties": {
        "document": {
          "properties": {
            "absolute_tolerance": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ]
            },
            "angle_tolerance_radians": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "null"
                }
              ]
            },
            "layer_count": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ]
            },
            "modified": {
              "anyOf": [
                {
                  "type": "boolean"
                },
                {
                  "type": "null"
                }
              ]
            },
            "object_count": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ]
            },
            "runtime_serial_number": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ]
            },
            "units": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ]
            }
          },
          "required": [
            "units",
            "absolute_tolerance",
            "angle_tolerance_radians",
            "modified",
            "layer_count",
            "object_count"
          ],
          "type": "object"
        },
        "layer_tree": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "한 줄에 한 레이어, 깊이마다 두 칸 들여쓴다. inspect_02-get_objects tool의 레이어 필터에는 부모부터 이름을 ::로 이은 전체 경로를 쓴다."
        },
        "layouts": {
          "anyOf": [
            {
              "items": {
                "properties": {
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  }
                },
                "required": [
                  "name",
                  "id"
                ],
                "type": "object"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ]
        },
        "locations": {
          "properties": {
            "artifact_dir": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "description": "현재 작업의 산출물 폴더"
            },
            "database": {
              "type": "string"
            },
            "loop_no": {
              "type": "integer"
            },
            "plan_artifact_dir": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "description": "Plan 전체 폴더"
            },
            "plan_id": {
              "type": "string"
            },
            "read_only": {
              "type": "boolean"
            },
            "step_id": {
              "type": "string"
            }
          },
          "required": [
            "database",
            "artifact_dir"
          ],
          "type": "object"
        },
        "named_views": {
          "anyOf": [
            {
              "items": {
                "properties": {
                  "id": {
                    "type": "string"
                  },
                  "name": {
                    "type": "string"
                  }
                },
                "required": [
                  "name",
                  "id"
                ],
                "type": "object"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "description": "이름과 ID는 capture_04-defined_view tool의 target에 쓸 수 있다."
        },
        "project": {
          "properties": {
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ]
            },
            "file_path": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ]
            },
            "files": {
              "description": "Phase·Scene에서 참조하는 프로젝트 등록 파일.",
              "items": {
                "properties": {
                  "description": {
                    "anyOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "file_name": {
                    "type": "string"
                  }
                },
                "required": [
                  "file_name",
                  "description"
                ],
                "type": "object"
              },
              "type": "array"
            },
            "files_page": {
              "properties": {
                "offset": {
                  "type": "integer"
                },
                "total": {
                  "type": "integer"
                }
              },
              "required": [
                "total",
                "offset"
              ],
              "type": "object"
            },
            "is_bound_document": {
              "type": "boolean"
            },
            "project_root": {
              "type": "string"
            },
            "worksession_files": {
              "anyOf": [
                {
                  "items": {
                    "properties": {
                      "file_path": {
                        "type": "string"
                      }
                    },
                    "required": [
                      "file_path"
                    ],
                    "type": "object"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "description": "현재 Rhino에 첨부한 파일. []는 첨부 없음, null은 조회 실패."
            }
          },
          "required": [
            "project_root",
            "file_name",
            "file_path",
            "is_bound_document",
            "files",
            "files_page",
            "worksession_files"
          ],
          "type": "object"
        },
        "runtime": {
          "properties": {
            "python_executable": {
              "type": "string"
            },
            "rhinocode": {
              "properties": {
                "available": {
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
                  "type": "string"
                },
                "version": {}
              },
              "required": [
                "available",
                "languages"
              ],
              "type": "object"
            },
            "scratch_root": {
              "type": "string"
            },
            "slot": {
              "type": "string"
            }
          },
          "required": [
            "slot",
            "scratch_root",
            "python_executable",
            "rhinocode"
          ],
          "type": "object"
        },
        "status": {
          "const": "success",
          "type": "string"
        },
        "warnings": {
          "description": "조회 실패나 뷰 목록 잘림을 알린다. Named View와 Layout은 각각 최대 128개다.",
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      },
      "required": [
        "status"
      ],
      "type": "object"
    },
    {
      "properties": {
        "error_code": {
          "type": "string"
        },
        "message": {
          "type": "string"
        },
        "status": {
          "const": "error",
          "type": "string"
        },
        "warnings": {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      },
      "required": [
        "status",
        "message"
      ],
      "type": "object"
    }
  ],
  "properties": {
    "document": {
      "properties": {
        "absolute_tolerance": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ]
        },
        "angle_tolerance_radians": {
          "anyOf": [
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ]
        },
        "layer_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "modified": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ]
        },
        "object_count": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "runtime_serial_number": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "units": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ]
        }
      },
      "required": [
        "units",
        "absolute_tolerance",
        "angle_tolerance_radians",
        "modified",
        "layer_count",
        "object_count"
      ],
      "type": "object"
    },
    "error_code": {
      "type": "string"
    },
    "layer_tree": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "한 줄에 한 레이어, 깊이마다 두 칸 들여쓴다. inspect_02-get_objects tool의 레이어 필터에는 부모부터 이름을 ::로 이은 전체 경로를 쓴다."
    },
    "layouts": {
      "anyOf": [
        {
          "items": {
            "properties": {
              "id": {
                "type": "string"
              },
              "name": {
                "type": "string"
              }
            },
            "required": [
              "name",
              "id"
            ],
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "locations": {
      "properties": {
        "artifact_dir": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "현재 작업의 산출물 폴더"
        },
        "database": {
          "type": "string"
        },
        "loop_no": {
          "type": "integer"
        },
        "plan_artifact_dir": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "Plan 전체 폴더"
        },
        "plan_id": {
          "type": "string"
        },
        "read_only": {
          "type": "boolean"
        },
        "step_id": {
          "type": "string"
        }
      },
      "required": [
        "database",
        "artifact_dir"
      ],
      "type": "object"
    },
    "message": {
      "type": "string"
    },
    "named_views": {
      "anyOf": [
        {
          "items": {
            "properties": {
              "id": {
                "type": "string"
              },
              "name": {
                "type": "string"
              }
            },
            "required": [
              "name",
              "id"
            ],
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "이름과 ID는 capture_04-defined_view tool의 target에 쓸 수 있다."
    },
    "project": {
      "properties": {
        "file_name": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ]
        },
        "file_path": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ]
        },
        "files": {
          "description": "Phase·Scene에서 참조하는 프로젝트 등록 파일.",
          "items": {
            "properties": {
              "description": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "file_name": {
                "type": "string"
              }
            },
            "required": [
              "file_name",
              "description"
            ],
            "type": "object"
          },
          "type": "array"
        },
        "files_page": {
          "properties": {
            "offset": {
              "type": "integer"
            },
            "total": {
              "type": "integer"
            }
          },
          "required": [
            "total",
            "offset"
          ],
          "type": "object"
        },
        "is_bound_document": {
          "type": "boolean"
        },
        "project_root": {
          "type": "string"
        },
        "worksession_files": {
          "anyOf": [
            {
              "items": {
                "properties": {
                  "file_path": {
                    "type": "string"
                  }
                },
                "required": [
                  "file_path"
                ],
                "type": "object"
              },
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "description": "현재 Rhino에 첨부한 파일. []는 첨부 없음, null은 조회 실패."
        }
      },
      "required": [
        "project_root",
        "file_name",
        "file_path",
        "is_bound_document",
        "files",
        "files_page",
        "worksession_files"
      ],
      "type": "object"
    },
    "runtime": {
      "properties": {
        "python_executable": {
          "type": "string"
        },
        "rhinocode": {
          "properties": {
            "available": {
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
              "type": "string"
            },
            "version": {}
          },
          "required": [
            "available",
            "languages"
          ],
          "type": "object"
        },
        "scratch_root": {
          "type": "string"
        },
        "slot": {
          "type": "string"
        }
      },
      "required": [
        "slot",
        "scratch_root",
        "python_executable",
        "rhinocode"
      ],
      "type": "object"
    },
    "status": {
      "enum": [
        "success",
        "error"
      ],
      "type": "string"
    },
    "warnings": {
      "anyOf": [
        {
          "description": "조회 실패나 뷰 목록 잘림을 알린다. Named View와 Layout은 각각 최대 128개다.",
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        }
      ]
    }
  },
  "required": [
    "status"
  ],
  "type": "object"
}
```

</details>


### 29. context_05-upsert_project_file

**beyond · RhinoTerminal**

```txt
프로젝트에 파일명을 등록하거나 설명을 갱신한다. 기존 파일은 등록된 대소문자와 실제 저장된 설명을 돌려준다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "생략하거나 null이면 기존 설명을 유지하고, 빈 문자열이면 지운다."
    },
    "file_name": {
      "description": "폴더를 제외한 파일명",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "file_name"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "생략하거나 null이면 기존 설명을 유지하고, 빈 문자열이면 지운다."
    },
    "file_name": {
      "description": "폴더를 제외한 파일명",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "anyOf": [
    {
      "properties": {
        "description": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ]
        },
        "file_name": {
          "type": "string"
        },
        "status": {
          "const": "success",
          "type": "string"
        }
      },
      "required": [
        "status",
        "file_name",
        "description"
      ],
      "type": "object"
    },
    {
      "properties": {
        "message": {
          "type": "string"
        },
        "status": {
          "const": "error",
          "type": "string"
        }
      },
      "required": [
        "status",
        "message"
      ],
      "type": "object"
    }
  ],
  "properties": {
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "file_name": {
      "type": "string"
    },
    "message": {
      "type": "string"
    },
    "status": {
      "enum": [
        "success",
        "error"
      ],
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "type": "object"
}
```

</details>


### 30. diagram_01-get

**beyond · RhinoTerminal**

```txt
다이어그램의 등록 정보와 원본 유무 조회. 치수는 `dimensions`, 경로는 `paths` 그룹으로 요청한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "diagram_02-list tool 또는 diagram_04-search tool의 ID를 그대로 사용.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "diagram_02-list tool 또는 diagram_04-search tool의 ID를 그대로 사용.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "asset": {
            "properties": {
              "category": {
                "type": "string"
              },
              "dimensions_mm": {
                "properties": {
                  "depth": {
                    "type": "number"
                  },
                  "height": {
                    "type": "number"
                  },
                  "width": {
                    "type": "number"
                  }
                },
                "type": "object"
              },
              "file": {
                "description": "라이브러리 기준 원본 상대 경로.",
                "type": "string"
              },
              "file_available": {
                "type": "boolean"
              },
              "name": {
                "type": "string"
              },
              "product": {
                "type": "string"
              },
              "source": {
                "additionalProperties": true,
                "type": "object"
              },
              "variant": {
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


### 31. diagram_02-list

**beyond · RhinoTerminal**

```txt
등록된 2D 다이어그램 목록. asset_id는 상세 조회와 배치에 사용한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "분류 전체 일치, 대소문자 무시. 기본값은 전체.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 20,
      "description": "1..50으로 보정. · 기본값 20",
      "type": "integer"
    },
    "offset": {
      "description": "다음 페이지에는 `next_offset` 사용. 기본값 0.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "분류 전체 일치, 대소문자 무시. 기본값은 전체.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 20,
      "description": "1..50으로 보정. · 기본값 20",
      "type": "integer"
    },
    "offset": {
      "description": "다음 페이지에는 `next_offset` 사용. 기본값 0.",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "properties": {
                "asset_id": {
                  "type": "string"
                },
                "category": {
                  "type": "string"
                },
                "dimensions_mm": {
                  "properties": {
                    "depth": {
                      "type": "number"
                    },
                    "height": {
                      "type": "number"
                    },
                    "width": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "file_available": {
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "product": {
                  "type": "string"
                },
                "variant": {
                  "type": "string"
                }
              },
              "required": [
                "asset_id"
              ],
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
          "next_offset": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
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


### 32. diagram_03-place

**beyond · RhinoTerminal**

```txt
도면 라이브러리의 SVG·DWG·DXF를 Rhino 블록으로 배치한다. 결과는 `object_guid`와 `bounds`로 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "rotation_degrees": {
      "description": "월드 Z축 기준 각도. 기본값 0°.",
      "type": "number"
    },
    "scale": {
      "description": "양수인 균일 축척. 기본값 1은 문서 단위로 환산한 원래 크기.",
      "type": "number"
    },
    "x": {
      "description": "삽입점 x·y·z는 Rhino 문서 단위. 기본값은 원점.",
      "type": "number"
    },
    "y": {
      "type": "number"
    },
    "z": {
      "type": "number"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "description": "목록·검색이 반환한 asset_id.",
      "type": "string"
    },
    "rotation_degrees": {
      "description": "월드 Z축 기준 각도. 기본값 0°.",
      "type": "number"
    },
    "scale": {
      "description": "양수인 균일 축척. 기본값 1은 문서 단위로 환산한 원래 크기.",
      "type": "number"
    },
    "x": {
      "description": "삽입점 x·y·z는 Rhino 문서 단위. 기본값은 원점.",
      "type": "number"
    },
    "y": {
      "type": "number"
    },
    "z": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "block_definition": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "bounds": {
            "anyOf": [
              {
                "properties": {
                  "max": {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "min": {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  }
                },
                "required": [
                  "min",
                  "max"
                ],
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
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
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "null이면 변경 적용 여부 미확인."
          },
          "mutation_state": {
            "description": "unknown·partial이면 문서에 변경이 남아 있을 수 있음.",
            "type": "string"
          },
          "object_guid": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "description": "inspect_02-get_objects tool과 Scene 구성원 입력에 전달할 블록 GUID."
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


### 33. diagram_04-search

**beyond · RhinoTerminal**

```txt
등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색한다. asset_id는 상세 조회와 배치에 사용한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "분류 전체 일치, 대소문자 무시. 기본값은 전체.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 10,
      "description": "1..50으로 보정. · 기본값 10",
      "type": "integer"
    },
    "max_depth_mm": {
      "description": "등록 치수는 추정치일 수 있다. 각 한계가 0 이하면 해당 치수 필터 해제.",
      "type": "number"
    },
    "max_height_mm": {
      "type": "number"
    },
    "max_width_mm": {
      "type": "number"
    },
    "offset": {
      "description": "다음 페이지에는 같은 필터와 `next_offset` 사용. 기본값 0.",
      "type": "integer"
    },
    "query": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "분류 전체 일치, 대소문자 무시. 기본값은 전체.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "dimensions",
              "drawing",
              "metadata",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 10,
      "description": "1..50으로 보정. · 기본값 10",
      "type": "integer"
    },
    "max_depth_mm": {
      "description": "등록 치수는 추정치일 수 있다. 각 한계가 0 이하면 해당 치수 필터 해제.",
      "type": "number"
    },
    "max_height_mm": {
      "type": "number"
    },
    "max_width_mm": {
      "type": "number"
    },
    "offset": {
      "description": "다음 페이지에는 같은 필터와 `next_offset` 사용. 기본값 0.",
      "type": "integer"
    },
    "query": {
      "description": "여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assets": {
            "items": {
              "properties": {
                "asset_id": {
                  "type": "string"
                },
                "category": {
                  "type": "string"
                },
                "dimensions_mm": {
                  "properties": {
                    "depth": {
                      "type": "number"
                    },
                    "height": {
                      "type": "number"
                    },
                    "width": {
                      "type": "number"
                    }
                  },
                  "type": "object"
                },
                "file_available": {
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "product": {
                  "type": "string"
                },
                "variant": {
                  "type": "string"
                }
              },
              "required": [
                "asset_id"
              ],
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
          "next_offset": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
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


### 34. drawing_01-apply_style

**beyond · RhinoTerminal**

```txt
수동 2D 작도에 사용할 표준 D 레이어와 속성을 적용한다. 작도 전에 용도에 맞는 layer_path를 선택하고, 반환된 레이어에서 객체의 선종을 ByLayer로 사용한다. D::PlanSection은 별도다. 다른 레시피를 지정한 경우에는 layer_path를 생략한다. print_display_review가 있으면 현재 연결과 일치하는 RhinoCode에서 Document 범위의 Model·Layout 인쇄 표시를 확인하고 필요할 때 macro를 실행한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "layer_path": {
      "enum": [
        "D::Section",
        "D::Elev",
        "D::Line",
        "D::Line::Hidden",
        "D::Line::Axis",
        "D::Dim",
        "D::Annotation",
        "D::Note",
        "D::Symbol",
        "D::Hatch"
      ],
      "type": "string"
    },
    "overwrite": {
      "description": "true로 표준 D 기존 정의 덮어쓰기. 생략하면 표준 D는 보존하고 다른 레이어는 덮어쓴다.",
      "type": "boolean"
    },
    "recipe_id": {
      "description": "기본 standard_d",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "layer_path": {
      "enum": [
        "D::Section",
        "D::Elev",
        "D::Line",
        "D::Line::Hidden",
        "D::Line::Axis",
        "D::Dim",
        "D::Annotation",
        "D::Note",
        "D::Symbol",
        "D::Hatch"
      ],
      "type": "string"
    },
    "overwrite": {
      "description": "true로 표준 D 기존 정의 덮어쓰기. 생략하면 표준 D는 보존하고 다른 레이어는 덮어쓴다.",
      "type": "boolean"
    },
    "recipe_id": {
      "description": "기본 standard_d",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                "linetype": {
                  "type": "string"
                },
                "path": {
                  "description": "inspect_02-get_objects tool의 filters.layer.include에 재사용 가능.",
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
          "print_display_review": {
            "description": "연결 모델의 Document PrintDisplay 확인이 필요할 때 반환",
            "properties": {
              "macro": {
                "type": "string"
              }
            },
            "required": [
              "macro"
            ],
            "type": "object"
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


### 35. drawing_02-get_recipe

**beyond · RhinoTerminal**

```txt
도면 스타일 레시피 조회. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "scales",
          "parameters",
          "source",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "recipe_id": {
      "description": "이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool의 recipe_id.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "recipe_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "items": {
        "enum": [
          "scales",
          "parameters",
          "source",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    },
    "recipe_id": {
      "description": "이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool의 recipe_id.",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "recipe": {
            "properties": {
              "annotations": {},
              "created_at": {},
              "description": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "display": {},
              "hatches": {},
              "layers": {
                "items": {
                  "additionalProperties": true,
                  "type": "object"
                },
                "type": "array"
              },
              "layout": {},
              "license": {},
              "linework": {},
              "name": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "output": {
                "additionalProperties": true,
                "type": "object"
              },
              "parameters": {},
              "projection": {
                "allOf": [
                  {
                    "properties": {
                      "type": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  {
                    "additionalProperties": true,
                    "type": "object"
                  }
                ]
              },
              "recommended_scales": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "references": {},
              "review_preparation": {},
              "scales": {},
              "source": {},
              "style": {},
              "units": {},
              "updated_at": {},
              "views": {}
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


### 36. drawing_04-import_hatches

**beyond · RhinoTerminal**

```txt
등록된 PAT의 패턴 정의를 가져오고 이름 목록을 반환한다. 같은 이름이 이미 있으면 기존 정의를 재사용한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "asset_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "patterns": {
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


### 37. drawing_05-list_recipes

**beyond · RhinoTerminal**

```txt
로드된 도면 스타일 레시피 목록. recipe_id는 drawing_02-get_recipe tool과 drawing_01-apply_style tool에서 사용.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "items": {
        "enum": [
          "scales",
          "parameters",
          "source",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "items": {
        "enum": [
          "scales",
          "parameters",
          "source",
          "audit",
          "all"
        ],
        "type": "string"
      },
      "type": "array"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "recipes": {
            "items": {
              "properties": {
                "annotations": {},
                "created_at": {},
                "description": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "display": {},
                "hatches": {},
                "layers": {
                  "items": {
                    "additionalProperties": true,
                    "type": "object"
                  },
                  "type": "array"
                },
                "layout": {},
                "license": {},
                "linework": {},
                "name": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "output": {
                  "additionalProperties": true,
                  "type": "object"
                },
                "parameters": {},
                "projection": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "recipe_id": {
                  "type": "string"
                },
                "recommended_scales": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "references": {},
                "review_preparation": {},
                "scales": {},
                "source": {},
                "style": {},
                "units": {},
                "updated_at": {},
                "views": {}
              },
              "required": [
                "recipe_id"
              ],
              "type": "object"
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


### 38. drawing_06-generate_plan_section

**beyond · RhinoTerminal**

```txt
클리핑 평면에서 도면을 생성·갱신·이동한다. Update는 기존 위치와 저장된 첨부 형상 설정을 사용한다. Create의 기본 범위는 활성 모델이다. include_attachments로 범위를 바꿀 수 있다. Move는 원점만 바꾼다. points는 클리핑 GUID별 문서 단위 절대 좌표다. 일부 클리핑만 끝날 수 있으므로 cuts와 unconfirmed_clipping_ids를 확인한다. Move에서는 모든 클리핑의 새 원점을 지정한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "operation": {
          "const": "Create",
          "type": "string"
        }
      }
    },
    {
      "properties": {
        "operation": {
          "const": "Update",
          "type": "string"
        },
        "points": false
      }
    },
    {
      "properties": {
        "far_dark": false,
        "far_width": false,
        "hatch": false,
        "include_attachments": false,
        "near_dark": false,
        "near_width": false,
        "operation": {
          "const": "Move",
          "type": "string"
        },
        "section_width_source": false,
        "small_details": false
      },
      "required": [
        "points"
      ]
    }
  ],
  "properties": {
    "clipping_ids": {
      "description": "활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.",
      "items": {
        "type": "string"
      },
      "minItems": 1,
      "type": "array"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "far_dark": {
      "description": "기본 45%, near_dark 이하",
      "type": "number"
    },
    "far_width": {
      "description": "기본 0.04 mm, near_width 이하",
      "type": "number"
    },
    "hatch": {
      "description": "기본 true, 원본 채움·형상에 따라 생성",
      "type": "boolean"
    },
    "include_attachments": {
      "type": "boolean"
    },
    "near_dark": {
      "description": "기본 80%",
      "type": "number"
    },
    "near_width": {
      "description": "기본 0.09 mm",
      "type": "number"
    },
    "operation": {
      "enum": [
        "Create",
        "Update",
        "Move"
      ],
      "type": "string"
    },
    "points": {
      "additionalProperties": {
        "anyOf": [
          {
            "items": {
              "type": "number"
            },
            "maxItems": 2,
            "minItems": 2,
            "type": "array"
          },
          {
            "items": {
              "type": "number"
            },
            "maxItems": 3,
            "minItems": 3,
            "type": "array"
          }
        ]
      },
      "type": "object"
    },
    "section_width_source": {
      "description": "기본 source, 원본 또는 D::PlanSection::Section 선폭",
      "enum": [
        "source",
        "output_layer"
      ],
      "type": "string"
    },
    "small_details": {
      "type": "boolean"
    }
  },
  "required": [
    "connection_id",
    "clipping_ids",
    "operation"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "operation": {
          "const": "Create",
          "type": "string"
        }
      }
    },
    {
      "properties": {
        "operation": {
          "const": "Update",
          "type": "string"
        },
        "points": false
      }
    },
    {
      "properties": {
        "far_dark": false,
        "far_width": false,
        "hatch": false,
        "include_attachments": false,
        "near_dark": false,
        "near_width": false,
        "operation": {
          "const": "Move",
          "type": "string"
        },
        "section_width_source": false,
        "small_details": false
      },
      "required": [
        "points"
      ]
    }
  ],
  "properties": {
    "clipping_ids": {
      "description": "활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.",
      "items": {
        "type": "string"
      },
      "minItems": 1,
      "type": "array"
    },
    "far_dark": {
      "description": "기본 45%, near_dark 이하",
      "type": "number"
    },
    "far_width": {
      "description": "기본 0.04 mm, near_width 이하",
      "type": "number"
    },
    "hatch": {
      "description": "기본 true, 원본 채움·형상에 따라 생성",
      "type": "boolean"
    },
    "include_attachments": {
      "type": "boolean"
    },
    "near_dark": {
      "description": "기본 80%",
      "type": "number"
    },
    "near_width": {
      "description": "기본 0.09 mm",
      "type": "number"
    },
    "operation": {
      "enum": [
        "Create",
        "Update",
        "Move"
      ],
      "type": "string"
    },
    "points": {
      "additionalProperties": {
        "anyOf": [
          {
            "items": {
              "type": "number"
            },
            "maxItems": 2,
            "minItems": 2,
            "type": "array"
          },
          {
            "items": {
              "type": "number"
            },
            "maxItems": 3,
            "minItems": 3,
            "type": "array"
          }
        ]
      },
      "type": "object"
    },
    "section_width_source": {
      "description": "기본 source, 원본 또는 D::PlanSection::Section 선폭",
      "enum": [
        "source",
        "output_layer"
      ],
      "type": "string"
    },
    "small_details": {
      "type": "boolean"
    }
  },
  "required": [
    "clipping_ids",
    "operation"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "completed": {
            "type": "integer"
          },
          "cuts": {
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
                  "required": [
                    "origin",
                    "xaxis",
                    "yaxis"
                  ],
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
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
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
                            "type": "string"
                          },
                          "target": {
                            "type": "string"
                          }
                        },
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "mutation_state": {
                      "type": "string"
                    },
                    "requires_reconciliation": {
                      "type": "boolean"
                    },
                    "tracked_changes_restored": {
                      "type": "boolean"
                    }
                  },
                  "type": "object"
                },
                "report": {
                  "additionalProperties": true,
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
          "error_code": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "type": "string"
          },
          "requested": {
            "description": "중복을 제외한 클리핑 수",
            "type": "integer"
          },
          "requires_reconciliation": {
            "type": "boolean"
          },
          "status": {
            "description": "timeout은 120초 취소 요청 뒤 중단·정리가 확인된 경우.",
            "enum": [
              "success",
              "partial",
              "cancelled",
              "timeout",
              "error"
            ],
            "type": "string"
          },
          "stop_reason": {
            "enum": [
              "deadline",
              "user"
            ],
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


### 39. grasshopper_01-get_logic

**beyond · RhinoTerminal**

```txt
색인된 로직의 물리 컴포넌트·설명·메타데이터 조회. JSON 단독 항목은 메타데이터를 반환한다. 연결 관계와 실행 가능성은 별도 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "logic_id": {
      "description": "grasshopper_03-list_library tool의 `logic_names`에서 선택.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "logic_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "logic_id": {
      "description": "grasshopper_03-list_library tool의 `logic_names`에서 선택.",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "error": {
            "description": "로직 미등록 시 grasshopper_03-list_library tool로 이름 조회.",
            "type": "string"
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
            "additionalProperties": true,
            "type": "object"
          },
          "source": {
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


### 40. grasshopper_02-list_capsules

**beyond · RhinoTerminal**

```txt
등록 캡슐의 기능과 실행 감사 상태를 최대 50개 조회한다. capsule_id로 실행한다. 포트 이름과 타입은 `field_groups: ["ports"]`로 확인한다. 정의 파일의 존재와 실행 결과는 별도 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "audited_only": {
      "type": "boolean"
    },
    "capability": {
      "description": "analyze, generate, form_find, aggregate. 대소문자 구분 없음.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "audited_only": {
      "type": "boolean"
    },
    "capability": {
      "description": "analyze, generate, form_find, aggregate. 대소문자 구분 없음.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                  "description": "`audited: true`인 ID를 grasshopper_04-run_definition tool에 전달.",
                  "type": "string"
                },
                "definition_file": {
                  "type": "string"
                },
                "input_ports": {
                  "description": "포트 이름은 실행의 `inputs`·`outputs` 키. 입력은 `required: false`일 때만 선택.",
                  "items": {
                    "properties": {
                      "description": {
                        "type": "string"
                      },
                      "name": {
                        "type": "string"
                      },
                      "required": {
                        "type": "boolean"
                      },
                      "type": {
                        "description": "[] 접미사는 배열.",
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
                "output_ports": {
                  "items": {
                    "properties": {
                      "description": {
                        "type": "string"
                      },
                      "name": {
                        "type": "string"
                      },
                      "type": {
                        "description": "[] 접미사는 배열.",
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
                "structure_type": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "title": {
                  "type": "string"
                }
              },
              "required": [
                "capsule_id"
              ],
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


### 41. grasshopper_03-list_library

**beyond · RhinoTerminal**

```txt
색인된 로직 이름 목록. `logic_names`를 grasshopper_01-get_logic tool에 전달한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "`paths` 또는 `all`로 라이브러리 경로 포함."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "ports",
              "definition",
              "source",
              "paths",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "`paths` 또는 `all`로 라이브러리 경로 포함."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "library_dir": {
            "type": "string"
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


### 42. grasshopper_04-run_definition

**beyond · RhinoTerminal**

```txt
실행 감사를 통과한 캡슐을 Rhino에서 계산한다. 출력 포트를 확인한 뒤 정의에 따라 하나의 Undo 기록으로 형상을 베이크한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "capsule_id": {
      "description": "grasshopper_02-list_capsules tool의 감사 통과 ID.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "inputs": {
      "additionalProperties": {
        "anyOf": [
          {
            "type": "number"
          },
          {
            "type": "string"
          },
          {
            "type": "boolean"
          },
          {
            "items": {
              "type": "number"
            },
            "type": "array"
          },
          {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          {
            "additionalProperties": false,
            "properties": {
              "guids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "required": [
              "guids"
            ],
            "type": "object"
          }
        ]
      },
      "description": "`ALMOND_IN_` 포트 이름과 `input_ports`의 타입·단위·필수 조건을 사용한다.",
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
      "description": "확률적 정의에만 정수 시드 사용"
    },
    "timeout_s": {
      "default": 60,
      "description": "솔버 시간 한도(초). 0 초과, 600 이하. · 기본값 60.0",
      "type": "number"
    }
  },
  "required": [
    "connection_id",
    "capsule_id",
    "inputs"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "capsule_id": {
      "description": "grasshopper_02-list_capsules tool의 감사 통과 ID.",
      "type": "string"
    },
    "inputs": {
      "additionalProperties": {
        "anyOf": [
          {
            "type": "number"
          },
          {
            "type": "string"
          },
          {
            "type": "boolean"
          },
          {
            "items": {
              "type": "number"
            },
            "type": "array"
          },
          {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          {
            "additionalProperties": false,
            "properties": {
              "guids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "required": [
              "guids"
            ],
            "type": "object"
          }
        ]
      },
      "description": "`ALMOND_IN_` 포트 이름과 `input_ports`의 타입·단위·필수 조건을 사용한다.",
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
      "description": "확률적 정의에만 정수 시드 사용"
    },
    "timeout_s": {
      "default": 60,
      "description": "솔버 시간 한도(초). 0 초과, 600 이하. · 기본값 60.0",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
            "description": "미등록 ID 요청 시 반환. 감사 상태는 목록에서 확인.",
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
            "description": "`unknown`이면 문서에 변경이 남을 수 있음.",
            "enum": [
              "none",
              "completed",
              "rolled_back",
              "unknown"
            ],
            "type": "string"
          },
          "outputs": {
            "additionalProperties": true,
            "description": "값의 의미·타입·단위는 캡슐 포트 계약을 따름",
            "type": "object"
          },
          "requires_reconciliation": {
            "description": "true 또는 응답 유실 시 `baked_guids`와 실제 문서 확인 후 재시도 판단.",
            "type": "boolean"
          },
          "status": {
            "type": "string"
          },
          "valid_inputs": {
            "description": "입력 검증 실패 시 유효한 입력 포트 이름.",
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


### 43. inspect_01-analyze_nested_blocks

**beyond · RhinoTerminal**

```txt
outline으로 중첩 블록 구조를 조회하고 resolve-block으로 공유 정의의 영향 범위와 참조·링크 제한을 확인한다. 후속 조회에 ID가 필요하면 include_ids=true를 지정한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "include_ids": {
      "type": "boolean"
    },
    "mode": {
      "enum": [
        "outline",
        "resolve-block"
      ],
      "type": "string"
    },
    "options": {
      "additionalProperties": true,
      "description": "outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.\ndepth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).\nfield_groups: summary(기본), objects, annotations, transforms. annotation_layer는 TextDot 레이어 필터. field_groups 생략 시 include_geometry·annotations로 상세 조회.\nresolve-block: options에는 최상위부터 대상까지 GUID 1..65개를 담은 path만 지정.",
      "type": "object"
    }
  },
  "required": [
    "connection_id",
    "mode",
    "options"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "include_ids": {
      "type": "boolean"
    },
    "mode": {
      "enum": [
        "outline",
        "resolve-block"
      ],
      "type": "string"
    },
    "options": {
      "additionalProperties": true,
      "description": "outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.\ndepth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).\nfield_groups: summary(기본), objects, annotations, transforms. annotation_layer는 TextDot 레이어 필터. field_groups 생략 시 include_geometry·annotations로 상세 조회.\nresolve-block: options에는 최상위부터 대상까지 GUID 1..65개를 담은 path만 지정.",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "data": {
            "properties": {
              "block_path_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "candidate_count": {
                "type": "integer"
              },
              "candidate_object_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "candidates_truncated": {
                "type": "boolean"
              },
              "definition": {
                "description": "resolve-block에서 확인한 조회 대상. 정의 배치 행렬은 행 우선 4×4 배열.",
                "type": "string"
              },
              "definition_impact": {
                "properties": {
                  "affected_root_count": {
                    "anyOf": [
                      {
                        "type": "integer"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "complete": {
                    "description": "영향 범위 계수 완료 여부와 반환 목록의 잘림 여부",
                    "type": "boolean"
                  },
                  "container_definitions": {
                    "items": {
                      "additionalProperties": true,
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "container_definitions_truncated": {
                    "type": "boolean"
                  },
                  "definition_is_reference": {
                    "type": "boolean"
                  },
                  "limits": {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "observed_affected_root_count": {
                    "type": "integer"
                  },
                  "observed_occurrence_count": {
                    "type": "integer"
                  },
                  "occurrence_count": {
                    "anyOf": [
                      {
                        "type": "integer"
                      },
                      {
                        "type": "null"
                      }
                    ]
                  },
                  "occurrences": {
                    "items": {
                      "additionalProperties": true,
                      "type": "object"
                    },
                    "type": "array"
                  },
                  "occurrences_truncated": {
                    "type": "boolean"
                  },
                  "source_archive_present": {
                    "type": "boolean"
                  },
                  "update_type": {
                    "type": "string"
                  }
                },
                "type": "object"
              },
              "definition_to_world": {
                "items": {
                  "type": "number"
                },
                "type": "array"
              },
              "depth_limited": {
                "type": "boolean"
              },
              "document_object": {
                "type": "boolean"
              },
              "editing_permission": {
                "type": "string"
              },
              "editor_owner_verified": {
                "type": "boolean"
              },
              "id": {
                "type": "string"
              },
              "items": {
                "type": "integer"
              },
              "layer": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "name": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "reason": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "records": {
                "items": {
                  "properties": {
                    "definition": {
                      "type": "string"
                    },
                    "definition_to_world": {
                      "description": "transforms의 행 우선 4×4 배열",
                      "items": {
                        "type": "number"
                      },
                      "type": "array"
                    },
                    "geometry_to_world": {
                      "items": {
                        "type": "number"
                      },
                      "type": "array"
                    },
                    "hidden": {
                      "type": "boolean"
                    },
                    "id": {
                      "description": "배치 객체 또는 정의 구성원의 ID. 편집 가능한 문서 객체 ID는 inspect_02-get_objects tool로 확인.",
                      "type": "string"
                    },
                    "kind": {
                      "enum": [
                        "summary",
                        "occurrence",
                        "owner",
                        "note",
                        "note_target"
                      ],
                      "type": "string"
                    },
                    "layer": {
                      "anyOf": [
                        {
                          "type": "string"
                        },
                        {
                          "type": "null"
                        }
                      ]
                    },
                    "locked": {
                      "type": "boolean"
                    },
                    "member_types": {
                      "additionalProperties": {
                        "type": "integer"
                      },
                      "type": "object"
                    },
                    "name": {
                      "anyOf": [
                        {
                          "type": "string"
                        },
                        {
                          "type": "null"
                        }
                      ]
                    },
                    "names": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "names_truncated": {
                      "type": "boolean"
                    },
                    "note_id": {
                      "type": "string"
                    },
                    "owner": {
                      "description": "annotations의 소유 범위와 TextDot",
                      "type": "string"
                    },
                    "path": {
                      "description": "공유 정의 영향을 조회할 때 resolve-block의 options.path에 재사용",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "point_local": {
                      "items": {
                        "type": "number"
                      },
                      "maxItems": 3,
                      "minItems": 3,
                      "type": "array"
                    },
                    "root_count": {
                      "description": "summary의 선택 범위 집계",
                      "type": "integer"
                    },
                    "text": {
                      "anyOf": [
                        {
                          "type": "string"
                        },
                        {
                          "type": "null"
                        }
                      ]
                    },
                    "text_limited": {
                      "type": "boolean"
                    },
                    "type": {
                      "type": "string"
                    },
                    "types": {
                      "additionalProperties": {
                        "type": "integer"
                      },
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "root_object_id": {
                "type": "string"
              },
              "selectable_now": {
                "type": "boolean"
              },
              "truncated": {
                "type": "boolean"
              },
              "type": {
                "type": "string"
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


### 44. inspect_02-get_objects

**beyond · RhinoTerminal**

```txt
현재·전체 문서·뷰포트에서 객체를 필터링한다. hierarchy는 그룹·블록을 펼친다. 다음 행 페이지에는 snapshot과 next_offset, 면 편집에는 최상위 객체 ID·geometry_crc·face_index를 사용한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "depth": {
      "description": "1..8, 루트=1(기본). 하위 깊이에는 recursive=true 필요.",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "expected_geometry_crcs": {
      "anyOf": [
        {
          "additionalProperties": {
            "maximum": 4294967295,
            "minimum": 0,
            "type": "integer"
          },
          "maxProperties": 4096,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부."
    },
    "expected_model_path": {
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "expected_snapshot": {
      "description": "offset > 0이면 첫 페이지의 snapshot 필요",
      "pattern": "^(?:[0-9a-f]{64})?$",
      "type": "string"
    },
    "face_limit": {
      "default": 128,
      "description": "1..128. objects 모드에서 사용. · 기본값 128",
      "maximum": 128,
      "minimum": 1,
      "type": "integer"
    },
    "face_offset": {
      "default": 0,
      "description": "양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요 · 기본값 0",
      "maximum": 100000,
      "minimum": 0,
      "type": "integer"
    },
    "fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
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
              ],
              "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
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
              ],
              "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "layer는 전체 경로 또는 GUID. group은 여러 값일 때 해당 쪽의 mode를 지정한다."
    },
    "group_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "maxItems": 64,
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
      "description": "서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가."
    },
    "include_geometry": {
      "description": "fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.",
      "type": "boolean"
    },
    "include_ids": {
      "type": "boolean"
    },
    "inside_window": {
      "description": "current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.",
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1..200 · 기본값 50",
      "maximum": 200,
      "minimum": 1,
      "type": "integer"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "maxItems": 4096,
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
      "description": "scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가."
    },
    "offset": {
      "description": "0..100000, 기본 0",
      "maximum": 100000,
      "minimum": 0,
      "type": "integer"
    },
    "recursive": {
      "description": "블록·그룹 하위를 펼친다.",
      "type": "boolean"
    },
    "result_mode": {
      "default": "objects",
      "description": "기본값 \"objects\". summary에서 recursive=true 사용 불가.",
      "enum": [
        "objects",
        "hierarchy",
        "summary"
      ],
      "type": "string"
    },
    "scope": {
      "default": "current",
      "description": "기본값 \"current\". document는 숨김·잠금 포함. inside_viewport는 current 중 활성 뷰 또는 Detail과 경계 상자가 교차하는 객체.",
      "enum": [
        "current",
        "document",
        "inside_viewport"
      ],
      "type": "string"
    },
    "selected": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "depth": {
      "description": "1..8, 루트=1(기본). 하위 깊이에는 recursive=true 필요.",
      "maximum": 8,
      "minimum": 1,
      "type": "integer"
    },
    "expected_geometry_crcs": {
      "anyOf": [
        {
          "additionalProperties": {
            "maximum": 4294967295,
            "minimum": 0,
            "type": "integer"
          },
          "maxProperties": 4096,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부."
    },
    "expected_model_path": {
      "description": "생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.",
      "type": "string"
    },
    "expected_snapshot": {
      "description": "offset > 0이면 첫 페이지의 snapshot 필요",
      "pattern": "^(?:[0-9a-f]{64})?$",
      "type": "string"
    },
    "face_limit": {
      "default": 128,
      "description": "1..128. objects 모드에서 사용. · 기본값 128",
      "maximum": 128,
      "minimum": 1,
      "type": "integer"
    },
    "face_offset": {
      "default": 0,
      "description": "양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요 · 기본값 0",
      "maximum": 100000,
      "minimum": 0,
      "type": "integer"
    },
    "fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
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
              ],
              "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
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
              ],
              "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
            }
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "layer는 전체 경로 또는 GUID. group은 여러 값일 때 해당 쪽의 mode를 지정한다."
    },
    "group_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "maxItems": 64,
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
      "description": "서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가."
    },
    "include_geometry": {
      "description": "fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.",
      "type": "boolean"
    },
    "include_ids": {
      "type": "boolean"
    },
    "inside_window": {
      "description": "current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.",
      "type": "boolean"
    },
    "limit": {
      "default": 50,
      "description": "1..200 · 기본값 50",
      "maximum": 200,
      "minimum": 1,
      "type": "integer"
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "maxItems": 4096,
          "minItems": 1,
          "type": "array",
          "uniqueItems": true
        },
        {
          "type": "null"
        }
      ],
      "description": "scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가."
    },
    "offset": {
      "description": "0..100000, 기본 0",
      "maximum": 100000,
      "minimum": 0,
      "type": "integer"
    },
    "recursive": {
      "description": "블록·그룹 하위를 펼친다.",
      "type": "boolean"
    },
    "result_mode": {
      "default": "objects",
      "description": "기본값 \"objects\". summary에서 recursive=true 사용 불가.",
      "enum": [
        "objects",
        "hierarchy",
        "summary"
      ],
      "type": "string"
    },
    "scope": {
      "default": "current",
      "description": "기본값 \"current\". document는 숨김·잠금 포함. inside_viewport는 current 중 활성 뷰 또는 Detail과 경계 상자가 교차하는 객체.",
      "enum": [
        "current",
        "document",
        "inside_viewport"
      ],
      "type": "string"
    },
    "selected": {
      "description": "current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.",
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "cycle_limited": {
            "type": "boolean"
          },
          "depth_limited": {
            "type": "boolean"
          },
          "editing": {
            "properties": {
              "mode": {
                "type": "string"
              },
              "stable": {
                "type": "boolean"
              },
              "target": {},
              "warnings": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "limitations": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "matched_count": {
            "type": "integer"
          },
          "membership_complete": {
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "next_offset": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ]
          },
          "nodes": {
            "items": {
              "properties": {
                "all_members_in_scope": {
                  "anyOf": [
                    {
                      "type": "boolean"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "block_path_ids": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "bounds": {
                  "anyOf": [
                    {
                      "properties": {
                        "max": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        },
                        "min": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        }
                      },
                      "required": [
                        "min",
                        "max"
                      ],
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "children_state": {
                  "type": "string"
                },
                "depth": {
                  "type": "integer"
                },
                "document_object": {
                  "type": "boolean"
                },
                "entity_kind": {
                  "type": "string"
                },
                "geometry_crc": {
                  "type": "integer"
                },
                "geometry_kind": {
                  "type": "string"
                },
                "groups": {
                  "items": {
                    "additionalProperties": true,
                    "type": "object"
                  },
                  "type": "array"
                },
                "groups_truncated": {
                  "type": "boolean"
                },
                "hidden": {
                  "type": "boolean"
                },
                "id": {
                  "type": "string"
                },
                "layer_path": {
                  "type": "string"
                },
                "locked": {
                  "type": "boolean"
                },
                "matched_member_count": {
                  "type": "integer"
                },
                "member_count": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "description": "전체 그룹 개수와 전체 포함 여부는 멤버십을 확인하지 못하면 null."
                },
                "membership_complete": {
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "number": {
                  "type": "integer"
                },
                "object_type": {
                  "type": "string"
                },
                "observed_member_count": {
                  "type": "integer"
                },
                "parent_number": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "root_object_id": {
                  "type": "string"
                },
                "selected": {
                  "type": "boolean"
                },
                "user_dictionary": {
                  "properties": {
                    "attributes": {
                      "properties": {
                        "total_keys": {
                          "type": "integer"
                        },
                        "truncated": {
                          "type": "boolean"
                        },
                        "values": {
                          "additionalProperties": true,
                          "type": "object"
                        }
                      },
                      "type": "object"
                    },
                    "geometry": {
                      "properties": {
                        "total_keys": {
                          "type": "integer"
                        },
                        "truncated": {
                          "type": "boolean"
                        },
                        "values": {
                          "additionalProperties": true,
                          "type": "object"
                        }
                      },
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "user_text": {
                  "properties": {
                    "total_keys": {
                      "type": "integer"
                    },
                    "truncated": {
                      "type": "boolean"
                    },
                    "values": {
                      "additionalProperties": true,
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "visible": {
                  "type": "boolean"
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "objects": {
            "items": {
              "properties": {
                "bounds": {
                  "anyOf": [
                    {
                      "properties": {
                        "max": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        },
                        "min": {
                          "items": {
                            "type": "number"
                          },
                          "maxItems": 3,
                          "minItems": 3,
                          "type": "array"
                        }
                      },
                      "required": [
                        "min",
                        "max"
                      ],
                      "type": "object"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "face_count": {
                  "type": "integer"
                },
                "face_edit_supported": {
                  "type": "boolean"
                },
                "face_page": {
                  "properties": {
                    "complete": {
                      "type": "boolean"
                    },
                    "next_offset": {
                      "anyOf": [
                        {
                          "type": "integer"
                        },
                        {
                          "type": "null"
                        }
                      ]
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
                      "bounds": {
                        "anyOf": [
                          {
                            "properties": {
                              "max": {
                                "items": {
                                  "type": "number"
                                },
                                "maxItems": 3,
                                "minItems": 3,
                                "type": "array"
                              },
                              "min": {
                                "items": {
                                  "type": "number"
                                },
                                "maxItems": 3,
                                "minItems": 3,
                                "type": "array"
                              }
                            },
                            "required": [
                              "min",
                              "max"
                            ],
                            "type": "object"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "face_edit_supported": {
                        "description": "기본 편집 조건만 확인한 값. 실제 편집 전에 형상 버전을 다시 검사.",
                        "type": "boolean"
                      },
                      "face_index": {
                        "description": "같은 관찰의 id·geometry_crc와 묶어 model_02-edit_planar_face tool의 object_id·face_index·expected_geometry_crc에 전달",
                        "type": "integer"
                      },
                      "normal": {
                        "anyOf": [
                          {
                            "items": {
                              "type": "number"
                            },
                            "maxItems": 3,
                            "minItems": 3,
                            "type": "array"
                          },
                          {
                            "type": "null"
                          }
                        ]
                      },
                      "planar": {
                        "type": "boolean"
                      },
                      "plane_origin": {
                        "anyOf": [
                          {
                            "items": {
                              "type": "number"
                            },
                            "maxItems": 3,
                            "minItems": 3,
                            "type": "array"
                          },
                          {
                            "type": "null"
                          }
                        ]
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
                "geometry_kind": {
                  "type": "string"
                },
                "geometry_valid": {
                  "type": "boolean"
                },
                "groups": {
                  "items": {
                    "additionalProperties": true,
                    "type": "object"
                  },
                  "type": "array"
                },
                "groups_truncated": {
                  "type": "boolean"
                },
                "hidden": {
                  "type": "boolean"
                },
                "id": {
                  "type": "string"
                },
                "layer_path": {
                  "type": "string"
                },
                "locked": {
                  "type": "boolean"
                },
                "manifold": {
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "object_type": {
                  "type": "string"
                },
                "selected": {
                  "type": "boolean"
                },
                "solid": {
                  "type": "boolean"
                },
                "user_dictionary": {
                  "properties": {
                    "attributes": {
                      "properties": {
                        "total_keys": {
                          "type": "integer"
                        },
                        "truncated": {
                          "type": "boolean"
                        },
                        "values": {
                          "additionalProperties": true,
                          "type": "object"
                        }
                      },
                      "type": "object"
                    },
                    "geometry": {
                      "properties": {
                        "total_keys": {
                          "type": "integer"
                        },
                        "truncated": {
                          "type": "boolean"
                        },
                        "values": {
                          "additionalProperties": true,
                          "type": "object"
                        }
                      },
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "user_text": {
                  "properties": {
                    "total_keys": {
                      "type": "integer"
                    },
                    "truncated": {
                      "type": "boolean"
                    },
                    "values": {
                      "additionalProperties": true,
                      "type": "object"
                    }
                  },
                  "type": "object"
                },
                "visible": {
                  "type": "boolean"
                },
                "volume": {
                  "anyOf": [
                    {
                      "type": "number"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "description": "문서 길이 단위의 세제곱. null은 계산 실패."
                }
              },
              "type": "object"
            },
            "type": "array"
          },
          "page_complete": {
            "type": "boolean"
          },
          "snapshot": {
            "description": "후속 행 조회의 expected_snapshot에 그대로 전달",
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "summary": {
            "items": {
              "properties": {
                "geometry_kind": {
                  "type": "string"
                },
                "layer_path": {
                  "type": "string"
                },
                "object_count": {
                  "type": "integer"
                },
                "object_type": {
                  "type": "string"
                },
                "visible_count": {
                  "type": "integer"
                }
              },
              "type": "object"
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


### 45. inspect_03-get_document_context

**beyond · RhinoTerminal**

```txt
연결 문서의 상태와 Named View·Layout·레이어 계층·표시 모드를 조회한다. Named View·Layout·표시 모드는 목록별 최대 128개이며 항상 ID를 반환한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_editor_details": {
      "description": "editor 요청 시 공급자·명령·Undo 근거 포함",
      "type": "boolean"
    },
    "include_ids": {
      "description": "뷰포트 등 선택적으로 ID를 반환하는 항목에 적용",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "document",
              "viewport",
              "editor",
              "viewports",
              "named_views",
              "layouts",
              "layer_tree",
              "display_modes"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "기본값: document, named_views, layouts, layer_tree, display_modes. []이면 조회 항목 없음."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_editor_details": {
      "description": "editor 요청 시 공급자·명령·Undo 근거 포함",
      "type": "boolean"
    },
    "include_ids": {
      "description": "뷰포트 등 선택적으로 ID를 반환하는 항목에 적용",
      "type": "boolean"
    },
    "sections": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "document",
              "viewport",
              "editor",
              "viewports",
              "named_views",
              "layouts",
              "layer_tree",
              "display_modes"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "기본값: document, named_views, layouts, layer_tree, display_modes. []이면 조회 항목 없음."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "display_modes": {
            "anyOf": [
              {
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
                "type": "array"
              },
              {
                "type": "null"
              }
            ]
          },
          "document": {
            "properties": {
              "absolute_tolerance": {
                "anyOf": [
                  {
                    "type": "number"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "문서 길이 단위"
              },
              "angle_tolerance": {
                "anyOf": [
                  {
                    "type": "number"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "라디안"
              },
              "layer_count": {
                "anyOf": [
                  {
                    "type": "number"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "modified": {
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "object_count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "units": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              }
            },
            "type": "object"
          },
          "editor": {
            "properties": {
              "evidence": {
                "additionalProperties": true,
                "type": "object"
              },
              "mode": {
                "type": "string"
              },
              "stable": {
                "type": "boolean"
              },
              "target": {},
              "warnings": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "type": "object"
          },
          "error_code": {
            "type": "string"
          },
          "layer_tree": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "layouts": {
            "anyOf": [
              {
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
                "type": "array"
              },
              {
                "type": "null"
              }
            ]
          },
          "message": {
            "type": "string"
          },
          "named_views": {
            "anyOf": [
              {
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
                "type": "array"
              },
              {
                "type": "null"
              }
            ]
          },
          "status": {
            "type": "string"
          },
          "viewport": {
            "anyOf": [
              {
                "additionalProperties": true,
                "type": "object"
              },
              {
                "type": "null"
              }
            ]
          },
          "viewports": {
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
            ]
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


### 46. inspect_04-get_selection_references

**beyond · RhinoTerminal**

```txt
저장된 Rhino 문서의 일반 모델에서 선택 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 조회한다. 선택과 일치한 Holon을 반환하며 Plan의 전체 대상은 별도 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "limit": {
      "default": 50,
      "description": "반환할 Plan 수 1..500 · 기본값 50",
      "type": "integer"
    },
    "selection_limit": {
      "default": 50,
      "description": "검사할 선택 객체 수 1..200 · 기본값 50",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "limit": {
      "default": 50,
      "description": "반환할 Plan 수 1..500 · 기본값 50",
      "type": "integer"
    },
    "selection_limit": {
      "default": 50,
      "description": "검사할 선택 객체 수 1..200 · 기본값 50",
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
              "additionalProperties": true,
              "type": "object"
            },
            "type": "array"
          },
          "message": {
            "type": "string"
          },
          "objects": {
            "description": "선택 객체의 등록 여부와 소유 Holon 포함",
            "items": {
              "additionalProperties": true,
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
              "additionalProperties": true,
              "type": "object"
            },
            "type": "array"
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
            "description": "반환한 Plan 목록의 잘림 여부",
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


### 47. inspect_05-resolve_targets

**beyond · RhinoTerminal**

```txt
Plan의 Scene 참조와 등록 Holon을 조회한다. Step을 지정하면 소속 Plan을 확인한다. 현재 Rhino 구성원은 별도 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "references, geometry, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "references, geometry, scope, audit, all. 생략·빈 배열이면 요약."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
              "additionalProperties": true,
              "type": "object"
            },
            "type": "array"
          },
          "message": {
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


### 48. intersect_01-find

**beyond · RhinoTerminal**

```txt
닫힌 솔리드 사이에 양의 부피가 겹치는 쌍을 센다. assessment=incomplete이면 전체 건수는 미확정이다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_block": {
      "description": "true이면 배치 변환을 적용해 중첩 블록 구성원까지 검사.",
      "type": "boolean"
    },
    "object_ids": {
      "description": "서로 다른 최상위 Rhino 객체 GUID 1..512개",
      "items": {
        "type": "string"
      },
      "type": "array"
    }
  },
  "required": [
    "connection_id",
    "object_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_block": {
      "description": "true이면 배치 변환을 적용해 중첩 블록 구성원까지 검사.",
      "type": "boolean"
    },
    "object_ids": {
      "description": "서로 다른 최상위 Rhino 객체 GUID 1..512개",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "assessment": {
            "const": "incomplete",
            "type": "string"
          },
          "document_units": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "description": "미판정 검사에서 확인한 문서 길이 단위"
          },
          "error_code": {
            "type": "string"
          },
          "failed_pairs": {
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
            "description": "미판정 쌍과 사유"
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
          "tolerance_model_units": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ],
            "description": "미판정 검사에서 확인한 모델 길이 공차"
          },
          "unsupported_objects": {
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
            "description": "검사할 수 없는 객체와 사유"
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


### 49. intersect_02-resolve

**beyond · RhinoTerminal**

```txt
겹치는 쌍을 비교해 선택한 객체에서 겹친 부분을 제거한다. 비교 시 실제 카메라와 선택이 바뀐다. 다음 검사에 실패하면 previous_result에서 직전 편집을 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "choice": {
      "anyOf": [
        {
          "const": 1,
          "type": "number"
        },
        {
          "const": 2,
          "type": "number"
        },
        {
          "const": "skip",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "review_id와 함께 지정. 1·2는 해당 번호 객체의 겹친 부분 제거, skip은 두 객체 유지."
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_block": {
      "description": "true이면 중첩 블록 구성원도 비교. 이 도구에서 블록에 속한 쌍은 skip만 지원.",
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
      "description": "새 검토에만 서로 다른 최상위 객체 GUID 1..512개 지정."
    },
    "review_id": {
      "description": "choice 제출에 사용할 현재 비교 ID. 이미 처리된 ID는 재사용 불가.",
      "type": "string"
    },
    "user_dictionary": {
      "anyOf": [
        {
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
          ],
          "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
        },
        {
          "type": "null"
        }
      ],
      "description": "새 검토의 UserDictionary 조건. 한 객체가 User Text와 UserDictionary 조건을 모두 충족해야 해당 쌍 표시."
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
                "type": "array"
              },
              "key": {
                "type": "string"
              }
            },
            "required": [
              "key",
              "any_of"
            ],
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "새 검토의 객체 속성 User Text 조건. 중첩 블록은 정의 구성원 속성 기준."
    }
  },
  "required": [
    "connection_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "choice": {
      "anyOf": [
        {
          "const": 1,
          "type": "number"
        },
        {
          "const": 2,
          "type": "number"
        },
        {
          "const": "skip",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "review_id와 함께 지정. 1·2는 해당 번호 객체의 겹친 부분 제거, skip은 두 객체 유지."
    },
    "include_block": {
      "description": "true이면 중첩 블록 구성원도 비교. 이 도구에서 블록에 속한 쌍은 skip만 지원.",
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
      "description": "새 검토에만 서로 다른 최상위 객체 GUID 1..512개 지정."
    },
    "review_id": {
      "description": "choice 제출에 사용할 현재 비교 ID. 이미 처리된 ID는 재사용 불가.",
      "type": "string"
    },
    "user_dictionary": {
      "anyOf": [
        {
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
          ],
          "description": "배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다."
        },
        {
          "type": "null"
        }
      ],
      "description": "새 검토의 UserDictionary 조건. 한 객체가 User Text와 UserDictionary 조건을 모두 충족해야 해당 쌍 표시."
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
                "type": "array"
              },
              "key": {
                "type": "string"
              }
            },
            "required": [
              "key",
              "any_of"
            ],
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "description": "새 검토의 객체 속성 User Text 조건. 중첩 블록은 정의 구성원 속성 기준."
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "assessment": {
      "const": "incomplete",
      "type": "string"
    },
    "document_units": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "미판정 검사에서 확인한 문서 길이 단위"
    },
    "error_code": {
      "type": "string"
    },
    "failed_pairs": {
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
      "description": "미판정 쌍과 사유"
    },
    "geometry_change_possible": {
      "type": "boolean"
    },
    "image_file": {
      "properties": {
        "path": {
          "type": "string"
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
    "mutation_state": {
      "type": "string"
    },
    "objects": {
      "items": {
        "properties": {
          "attributes": {
            "properties": {
              "user_strings": {
                "properties": {
                  "total_keys": {
                    "type": "integer"
                  },
                  "truncated": {
                    "type": "boolean"
                  },
                  "values": {
                    "additionalProperties": true,
                    "type": "object"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          },
          "guid": {
            "type": "string"
          },
          "handle": {
            "properties": {
              "object_id": {
                "type": "string"
              },
              "path": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            },
            "required": [
              "object_id",
              "path"
            ],
            "type": "object"
          },
          "member_id": {
            "type": "string"
          },
          "number": {
            "type": "integer"
          },
          "user_dictionary": {
            "additionalProperties": true,
            "description": "객체 속성과 형상의 UserDictionary를 구분",
            "type": "object"
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "overlap": {
      "properties": {
        "method": {
          "type": "string"
        },
        "status": {
          "type": "string"
        },
        "volume_model_units3": {
          "type": "number"
        }
      },
      "type": "object"
    },
    "previous_result": {
      "properties": {
        "edited": {
          "type": "boolean"
        },
        "geometry_crc": {
          "type": "integer"
        },
        "keep_id": {
          "type": "string"
        },
        "status": {
          "enum": [
            "resolved",
            "skipped"
          ],
          "type": "string"
        },
        "trim_id": {
          "type": "string"
        }
      },
      "type": "object"
    },
    "regions": {
      "items": {
        "properties": {
          "bounds": {
            "items": {
              "items": {
                "type": "number"
              },
              "type": "array"
            },
            "type": "array"
          },
          "centroid": {
            "anyOf": [
              {
                "items": {
                  "type": "number"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ]
          },
          "region_index": {
            "type": "integer"
          },
          "volume_model_units3": {
            "anyOf": [
              {
                "type": "number"
              },
              {
                "type": "null"
              }
            ]
          }
        },
        "type": "object"
      },
      "type": "array"
    },
    "requires_reconciliation": {
      "type": "boolean"
    },
    "review_id": {
      "type": "string"
    },
    "skipped_pairs": {
      "type": "number"
    },
    "state": {
      "enum": [
        "awaiting_choice",
        "completed"
      ],
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "tolerance_model_units": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "description": "미판정 검사에서 확인한 모델 길이 공차"
    },
    "unsupported_objects": {
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
      "description": "검사할 수 없는 객체와 사유"
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


### 50. model_01-assign_material

**beyond · RhinoTerminal**

```txt
층·구조 역할을 기록하고 재료를 ByLayer로 적용한다. applied_guids는 처리 성공, changed_guids는 실제 변경 대상이다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "apply_render_material": {
      "description": "기본 true. 재료 레이어(기본 M::<category>::<material_id>)에 배치하며 새 레이어에만 스타일을 적용. false는 메타데이터만 기록.",
      "type": "boolean"
    },
    "attach_metadata": {
      "description": "렌더 재료 적용 시 User Text에 material_id도 기록.",
      "type": "boolean"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "construction_detail": {
      "description": "생략·공백이면 키가 없는 객체에만 공백 한 칸을 기록.",
      "type": "string"
    },
    "construction_reference": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string"
            },
            "kind": {
              "const": "construction_system",
              "type": "string"
            }
          },
          "required": [
            "kind",
            "id"
          ],
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "id는 구법 라이브러리의 system_id. 생략 시 키가 없는 객체에만 공백 한 칸을 기록."
    },
    "floor": {
      "description": "객체 속성 UserDictionary의 Floor에 기록. 기존 User Text의 floor는 유지.",
      "type": "string"
    },
    "guids": {
      "description": "현재 Rhino 객체 GUID",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "material_id": {
      "description": "model_04-list_materials tool의 materials[].material_id",
      "type": "string"
    },
    "structural_role": {
      "description": "객체 속성 User Text의 structural_role에 기록하는 모델 분류. 해석 설정은 별도.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "floor",
    "guids",
    "material_id",
    "structural_role"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "apply_render_material": {
      "description": "기본 true. 재료 레이어(기본 M::<category>::<material_id>)에 배치하며 새 레이어에만 스타일을 적용. false는 메타데이터만 기록.",
      "type": "boolean"
    },
    "attach_metadata": {
      "description": "렌더 재료 적용 시 User Text에 material_id도 기록.",
      "type": "boolean"
    },
    "construction_detail": {
      "description": "생략·공백이면 키가 없는 객체에만 공백 한 칸을 기록.",
      "type": "string"
    },
    "construction_reference": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "id": {
              "type": "string"
            },
            "kind": {
              "const": "construction_system",
              "type": "string"
            }
          },
          "required": [
            "kind",
            "id"
          ],
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "id는 구법 라이브러리의 system_id. 생략 시 키가 없는 객체에만 공백 한 칸을 기록."
    },
    "floor": {
      "description": "객체 속성 UserDictionary의 Floor에 기록. 기존 User Text의 floor는 유지.",
      "type": "string"
    },
    "guids": {
      "description": "현재 Rhino 객체 GUID",
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "material_id": {
      "description": "model_04-list_materials tool의 materials[].material_id",
      "type": "string"
    },
    "structural_role": {
      "description": "객체 속성 User Text의 structural_role에 기록하는 모델 분류. 해석 설정은 별도.",
      "type": "string"
    }
  },
  "required": [
    "floor",
    "guids",
    "material_id",
    "structural_role"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "applied_guids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "changed_guids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "layer_action": {
            "enum": [
              "created",
              "reused",
              "not_applied"
            ],
            "type": "string"
          },
          "layer_changed_guids": {
            "description": "실제로 다른 레이어로 옮긴 객체 GUID. 같은 레이어에서 ByLayer만 복구했으면 제외.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "layer_path": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "description": "자동 배정한 전체 레이어 경로. 메타데이터 전용 호출이면 null."
          },
          "material_metadata_attached": {
            "description": "렌더 재료와 함께 material_id를 기록하고 확인한 대상이 있는지 표시",
            "type": "boolean"
          },
          "message": {
            "type": "string"
          },
          "mutation_state": {
            "type": "string"
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


### 51. model_02-edit_planar_face

**beyond · RhinoTerminal**

```txt
일반 모델에서 닫힌 Brep의 평면 한 면을 PushPull Extend로 이동한다. 편집 후 후속 작업에 필요한 faces와 geometry_crc를 다시 조회한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_geometry_crc": {
      "description": "면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.",
      "maximum": 4294967295,
      "minimum": 0,
      "type": "integer"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "face_index": {
      "description": "같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.",
      "maximum": 2147483647,
      "minimum": 0,
      "type": "integer"
    },
    "object_id": {
      "description": "연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID",
      "type": "string"
    },
    "translation": {
      "description": "문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.",
      "items": {
        "type": "number"
      },
      "maxItems": 3,
      "minItems": 3,
      "type": "array"
    }
  },
  "required": [
    "connection_id",
    "expected_geometry_crc",
    "face_index",
    "object_id",
    "translation"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_geometry_crc": {
      "description": "면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.",
      "maximum": 4294967295,
      "minimum": 0,
      "type": "integer"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "face_index": {
      "description": "같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.",
      "maximum": 2147483647,
      "minimum": 0,
      "type": "integer"
    },
    "object_id": {
      "description": "연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID",
      "type": "string"
    },
    "translation": {
      "description": "문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.",
      "items": {
        "type": "number"
      },
      "maxItems": 3,
      "minItems": 3,
      "type": "array"
    }
  },
  "required": [
    "expected_geometry_crc",
    "face_index",
    "object_id",
    "translation"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "mutation_state": {
            "type": "string"
          },
          "requires_reconciliation": {
            "type": "boolean"
          },
          "result": {
            "properties": {
              "edited": {
                "type": "boolean"
              },
              "geometry_crc": {
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


### 52. model_03-edit_planar_faces

**beyond · RhinoTerminal**

```txt
일반 모델에서 서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동한다. 준비 단계에서 한 항목이라도 거부되면 객체 교체를 시작하지 않는다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "edits": {
      "description": "서로 다른 Brep 1..32개. 각 항목은 model_02-edit_planar_face tool의 입력 조건 적용.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "expected_geometry_crc": {
            "type": "integer"
          },
          "face_index": {
            "type": "integer"
          },
          "object_id": {
            "type": "string"
          },
          "translation": {
            "items": {
              "type": "number"
            },
            "maxItems": 3,
            "minItems": 3,
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
      },
      "maxItems": 32,
      "minItems": 1,
      "type": "array"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "edits"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "edits": {
      "description": "서로 다른 Brep 1..32개. 각 항목은 model_02-edit_planar_face tool의 입력 조건 적용.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "expected_geometry_crc": {
            "type": "integer"
          },
          "face_index": {
            "type": "integer"
          },
          "object_id": {
            "type": "string"
          },
          "translation": {
            "items": {
              "type": "number"
            },
            "maxItems": 3,
            "minItems": 3,
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
      },
      "maxItems": 32,
      "minItems": 1,
      "type": "array"
    },
    "expected_model_path": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "mutation_state": {
            "type": "string"
          },
          "requires_reconciliation": {
            "type": "boolean"
          },
          "result": {
            "description": "객체 교체 중 실패하면 일부 편집이 남을 수 있다.",
            "properties": {
              "applied_count": {
                "type": "integer"
              },
              "complete": {
                "type": "boolean"
              },
              "items": {
                "description": "입력 순서의 항목별 결과. 실패 단계와 메시지 포함.",
                "items": {
                  "properties": {
                    "geometry_crc": {
                      "description": "다음 면 편집 전 면 인덱스와 CRC를 다시 조회",
                      "type": "number"
                    },
                    "message": {
                      "type": "string"
                    },
                    "stage": {
                      "enum": [
                        "prepare",
                        "recheck",
                        "replace"
                      ],
                      "type": "string"
                    },
                    "status": {
                      "enum": [
                        "applied",
                        "rejected",
                        "failed",
                        "unknown",
                        "not_attempted"
                      ],
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


### 53. model_04-list_materials

**beyond · RhinoTerminal**

```txt
라이브러리에서 이름·ID·설명·태그나 분류로 재료를 검색한다. material_id는 model_01-assign_material tool에 전달한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "query": {
      "description": "대소문자 구분 없는 부분 일치",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
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
      "description": "display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약."
    },
    "query": {
      "description": "대소문자 구분 없는 부분 일치",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "library_dir": {
            "type": "string"
          },
          "materials": {
            "items": {
              "properties": {
                "base_color": {
                  "description": "display",
                  "items": {
                    "type": "number"
                  },
                  "type": "array"
                },
                "category": {
                  "type": "string"
                },
                "created_at": {},
                "density": {
                  "description": "physical",
                  "type": "number"
                },
                "density_kg_m3": {
                  "type": "number"
                },
                "description": {
                  "description": "metadata, source, paths, audit",
                  "type": "string"
                },
                "emission": {},
                "file": {
                  "type": "string"
                },
                "ior": {
                  "type": "number"
                },
                "license": {},
                "material_id": {
                  "type": "string"
                },
                "metallic": {
                  "type": "number"
                },
                "name": {
                  "type": "string"
                },
                "opacity": {
                  "type": "number"
                },
                "physical": {},
                "provenance": {},
                "roughness": {
                  "type": "number"
                },
                "source": {},
                "structural_material": {},
                "tags": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "textures": {},
                "ue_material_slot": {
                  "type": "string"
                },
                "updated_at": {}
              },
              "required": [
                "material_id"
              ],
              "type": "object"
            },
            "type": "array"
          },
          "message": {
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


### 54. plan_02-create

**beyond · RhinoTerminal**

```txt
Phase 또는 Plan을 만든다. Plan은 scope에 맞는 Step과 회차 0에서 시작한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "anyOf": [
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
              "description": "같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "description": {
              "type": "string"
            },
            "file_name": {
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명.",
              "items": {
                "type": "string"
              },
              "type": "array"
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
              "description": "Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "status": {
              "default": "pending",
              "description": "기본값 \"pending\"",
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
              ]
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
              "description": "상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "phase_id": {
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
              "description": "작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
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
              ]
            },
            "scope": {
              "default": "house",
              "description": "Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능. · 기본값 \"house\"",
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
            "goal",
            "title"
          ],
          "type": "object"
        }
      ]
    }
  },
  "required": [
    "connection_id",
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "anyOf": [
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
              "description": "같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음."
            },
            "description": {
              "type": "string"
            },
            "file_name": {
              "description": "context_04-get_project_info tool의 `project.files`에 등록된 파일명.",
              "items": {
                "type": "string"
              },
              "type": "array"
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
              "description": "Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
            },
            "status": {
              "default": "pending",
              "description": "기본값 \"pending\"",
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
              ]
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
              "description": "상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음."
            },
            "phase_id": {
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
              "description": "작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음."
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
              ]
            },
            "scope": {
              "default": "house",
              "description": "Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능. · 기본값 \"house\"",
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
            "goal",
            "title"
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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

**beyond · RhinoTerminal**

```txt
새 회차를 시작하거나 resume으로 최신 회차를 재개한다. plan_10-set_working tool의 step_id에 next_step_id를 전달해 Step을 선택한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "description": "최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "feedback": {
      "description": "재개 시 생략하거나 비우면 이전 피드백 유지.",
      "type": "string"
    },
    "plan_id": {
      "description": "plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.",
      "type": "string"
    },
    "resume": {
      "description": "`true`면 최신 회차 재개, `false`면 새 회차 시작.",
      "type": "boolean"
    }
  },
  "required": [
    "connection_id",
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "description": "최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.",
      "type": "string"
    },
    "feedback": {
      "description": "재개 시 생략하거나 비우면 이전 피드백 유지.",
      "type": "string"
    },
    "plan_id": {
      "description": "plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.",
      "type": "string"
    },
    "resume": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
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
    "next_step_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "다음 작업으로 선택할 첫 미완료 Step."
    },
    "plan_artifact_dir": {
      "type": "string"
    },
    "plan_id": {
      "type": "string"
    },
    "plan_status": {
      "description": "회차를 시작해도 Plan 상태는 유지.",
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
    "previous_loop": {
      "anyOf": [
        {
          "properties": {
            "loop_no": {
              "type": "integer"
            },
            "steps": {
              "items": {
                "properties": {
                  "depends_on": {
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
                  "name": {
                    "type": "string"
                  },
                  "output_refs": {
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  },
                  "status": {
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
                  "step_id": {
                    "type": "string"
                  },
                  "step_type": {
                    "type": "string"
                  },
                  "takeaways": {
                    "type": "string"
                  }
                },
                "required": [
                  "step_id",
                  "name",
                  "step_type",
                  "status"
                ],
                "type": "object"
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
      "description": "첫 회차에는 실행 전 0번 기록을 포함할 수 있음."
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
          "depends_on": {
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
          "name": {
            "type": "string"
          },
          "output_refs": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "status": {
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
          "step_id": {
            "type": "string"
          },
          "step_type": {
            "type": "string"
          },
          "takeaways": {
            "type": "string"
          }
        },
        "required": [
          "step_id",
          "name",
          "step_type",
          "status"
        ],
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

**beyond · RhinoTerminal**

```txt
Phase·Plan·Step 작업 기록 조회. `include_details=true`로 상세를 포함. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로로 열어 확인.

Plan·Step 조회에 `revision`을 지정하면 현재 번호여도 읽기 전용 스냅샷 반환.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
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
    "connection_id",
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "include_details": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ]
              }
            },
            "type": "object"
          },
          "phase_id": {
            "type": "string"
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
                "anyOf": [
                  {
                    "properties": {
                      "name": {
                        "type": "string"
                      },
                      "phase_id": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "previous_id": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
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
                    "name": {
                      "type": "string"
                    },
                    "status": {
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
                    "step_id": {
                      "type": "string"
                    },
                    "step_type": {
                      "type": "string"
                    }
                  },
                  "required": [
                    "step_id",
                    "name",
                    "step_type",
                    "status"
                  ],
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
                "const": "error",
                "type": "string"
              }
            ]
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
          "step_id": {
            "type": "string"
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

**beyond · RhinoTerminal**

```txt
Plan 리비전 목록을 최신 회차·리비전 순으로 조회. Step 필터는 해당 Step의 직접 변경만 포함. `offset` 미지원.

과거 기록은 plan_05-get tool에 같은 `loop_no`와 `revision`을 넣어 조회.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "`audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환."
    },
    "limit": {
      "default": 50,
      "description": "1~500. · 기본값 50",
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
      "description": "생략·`null`은 모든 회차, 0은 실행 전 기록."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
      "description": "생략하거나 비우면 Step으로 필터링하지 않음.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "`audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환."
    },
    "limit": {
      "default": 50,
      "description": "1~500. · 기본값 50",
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
      "description": "생략·`null`은 모든 회차, 0은 실행 전 기록."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
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

**beyond · RhinoTerminal**

```txt
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록 조회. `offset` 미지원. Step 목록과 리비전 정보는 같은 스냅샷을 기준으로 반환.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "anyOf": [
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
              "description": "`description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환."
            },
            "limit": {
              "default": 50,
              "description": "1~500. · 기본값 50",
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
              "description": "1~500. · 기본값 50",
              "type": "integer"
            },
            "phase_id": {
              "description": "생략하거나 비우면 Phase 소속 여부와 관계없이 조회.",
              "type": "string"
            },
            "scene_id": {
              "description": "생략하거나 비우면 Scene 연결 여부와 관계없이 조회.",
              "type": "string"
            },
            "status": {
              "anyOf": [
                {
                  "const": "",
                  "type": "string"
                },
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
                }
              ],
              "description": "생략하거나 비우면 상태 필터를 적용하지 않음."
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
              "description": "1~500. 정의된 순서의 앞부분을 반환. · 값 1~500 · 기본값 50",
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
    "connection_id",
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "anyOf": [
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
              "description": "`description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환."
            },
            "limit": {
              "default": 50,
              "description": "1~500. · 기본값 50",
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
              "description": "1~500. · 기본값 50",
              "type": "integer"
            },
            "phase_id": {
              "description": "생략하거나 비우면 Phase 소속 여부와 관계없이 조회.",
              "type": "string"
            },
            "scene_id": {
              "description": "생략하거나 비우면 Scene 연결 여부와 관계없이 조회.",
              "type": "string"
            },
            "status": {
              "anyOf": [
                {
                  "const": "",
                  "type": "string"
                },
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
                }
              ],
              "description": "생략하거나 비우면 상태 필터를 적용하지 않음."
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
              "description": "1~500. 정의된 순서의 앞부분을 반환. · 값 1~500 · 기본값 50",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "phases": {
            "items": {
              "properties": {
                "created_at": {
                  "description": "`audit` 또는 `all` 그룹에서 반환.",
                  "type": "string"
                },
                "depends_on": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "description": {
                  "description": "`description` 또는 `all` 그룹에서 반환.",
                  "type": "string"
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
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "status": {
                  "type": "string"
                },
                "updated_at": {
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
                "name": {
                  "type": "string"
                },
                "status": {
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
                "step_id": {
                  "type": "string"
                },
                "step_type": {
                  "type": "string"
                }
              },
              "required": [
                "step_id",
                "name",
                "step_type",
                "status"
              ],
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

**beyond · RhinoTerminal**

```txt
첫 Loop를 시작하기 전에 현재 Plan의 산출물 폴더명을 바꾼다. 먼저 plan_10-set_working tool로 폴더를 만든다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "name": {
      "description": "경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.",
      "type": "string"
    },
    "plan_id": {
      "description": "생략하거나 비우면 현재 선택된 Plan 사용.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "description": "경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.",
      "type": "string"
    },
    "plan_id": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "error_code": {
      "type": "string"
    },
    "message": {
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

**beyond · RhinoTerminal**

```txt
현재 연결의 산출물 작업 대상으로 Plan과 선택적인 Step 지정. 작업 실행과 Plan·Step 상태 변경은 별도.

최초 선택에서 산출물 경로를 정하면 리비전이 증가할 수 있음. 이후 같은 경로 재사용. `artifact_dir`은 Loop 시작 전 Plan 루트, 시작 후 현재 회차 폴더.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
      "description": "최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "지정한 회차가 최신 회차인지 확인한다."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
      "description": "생략하면 Plan만 선택.",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "plan_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "artifact_name": {
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
      "description": "지정한 회차가 최신 회차인지 확인한다."
    },
    "plan_id": {
      "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
      "type": "string"
    },
    "step_id": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "description": "script_01-run_project_python tool의 작업 디렉터리."
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

**beyond · RhinoTerminal**

```txt
Phase·Plan 작업 정보 또는 Step 상태·입출력 참조·판단 기록 수정. Plan·Step은 현재 회차만 수정 가능.

`depends_on`, `input_refs`, `output_refs`는 `add`/`remove` 패치. 나머지 대상·산출물·상하위 관계 배열은 전체 교체. 생략·`null`은 기존 값 유지, 교체 배열의 `[]`는 전체 삭제.

응답 `status`는 모두 반영해 값이 바뀌면 `updated`, 바뀐 값이 없으면 `no_change`, 변경과 건너뛴 항목이 함께 있으면 `partial_success`. 이미 추가된 값, 없어서 지울 수 없는 값, 중복·잘못된 값과 두 목록에 동시에 넣은 값은 issues에서 확인. Step을 `completed`로 지정하면 함께 전달한 필드와 한 번에 저장.

Plan 완료는 사용자 확인 후 지정.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "request": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              "description": "빈 문자열은 설명 삭제."
            },
            "file_name": {
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
              "description": "project.files에 등록된 파일명. []는 연결 해제."
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
              "description": "빈 이름은 거부."
            },
            "phase_id": {
              "description": "plan_08-list tool의 `request.target=\"phase\"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 phase_id.",
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
              ]
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
              ]
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
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
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
              "description": "빈 문자열은 Phase 소속 해제."
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
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
              ]
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
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "input_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
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
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "output_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
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
              ]
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
    "connection_id",
    "request"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "anyOf": [
        {
          "additionalProperties": false,
          "properties": {
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              "description": "빈 문자열은 설명 삭제."
            },
            "file_name": {
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
              "description": "project.files에 등록된 파일명. []는 연결 해제."
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
              "description": "빈 이름은 거부."
            },
            "phase_id": {
              "description": "plan_08-list tool의 `request.target=\"phase\"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 phase_id.",
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
              ]
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
              ]
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
              "description": "상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
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
              "description": "빈 문자열은 Phase 소속 해제."
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
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
              ]
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
              "description": "현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정."
            },
            "input_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
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
              "description": "현재 회차만 허용. 생략하면 현재 회차 적용."
            },
            "output_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "properties": {
                    "add": {
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
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
              ]
            },
            "plan_id": {
              "description": "plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id",
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
              ]
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
            ],
            "type": "string"
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
          "phase": {
            "properties": {
              "phase_id": {
                "type": "string"
              },
              "status": {
                "enum": [
                  "pending",
                  "running",
                  "paused",
                  "completed",
                  "failed",
                  "blocked"
                ],
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
                "enum": [
                  "pending",
                  "running",
                  "paused",
                  "completed",
                  "failed",
                  "blocked"
                ],
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
              "status": {
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

**beyond · RhinoTerminal**

```txt
구법 후보와 예비 부재 깊이 조회. `field_groups`를 생략하면 요약을 반환한다. 부재 깊이와 재료 참조는 `rules`를 요청한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "floor, wall, roof, foundation. 기본값은 전체.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_reference_data": {
      "description": "`load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.",
      "type": "boolean"
    },
    "material": {
      "description": "`Wood`, `Steel`, `Concrete`. `S355`는 `Steel`로 조회.",
      "type": "string"
    },
    "query": {
      "description": "예: `glulam`, `longspan`, `bearing wall`.",
      "type": "string"
    },
    "span_m": {
      "description": "양수면 경간 적합 여부와 권장 깊이 계산. 벽 구법에는 비지지 높이.",
      "type": "number"
    },
    "structure_type": {
      "description": "`beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "description": "floor, wall, roof, foundation. 기본값은 전체.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_reference_data": {
      "description": "`load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.",
      "type": "boolean"
    },
    "material": {
      "description": "`Wood`, `Steel`, `Concrete`. `S355`는 `Steel`로 조회.",
      "type": "string"
    },
    "query": {
      "description": "예: `glulam`, `longspan`, `bearing wall`.",
      "type": "string"
    },
    "span_m": {
      "description": "양수면 경간 적합 여부와 권장 깊이 계산. 벽 구법에는 비지지 높이.",
      "type": "number"
    },
    "structure_type": {
      "description": "`beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "reference": {
            "properties": {
              "egress_rules": {
                "additionalProperties": true,
                "type": "object"
              },
              "live_loads_kpa": {
                "additionalProperties": {
                  "type": "number"
                },
                "type": "object"
              },
              "material_densities_kg_m3": {
                "additionalProperties": {
                  "type": "number"
                },
                "type": "object"
              },
              "notes": {
                "type": "string"
              }
            },
            "required": [
              "live_loads_kpa",
              "material_densities_kg_m3",
              "egress_rules",
              "notes"
            ],
            "type": "object"
          },
          "source": {
            "type": "string"
          },
          "systems": {
            "items": {
              "properties": {
                "category": {
                  "type": "string"
                },
                "depth_guidance": {
                  "items": {
                    "properties": {
                      "element": {
                        "type": "string"
                      },
                      "rule": {
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
                  "description": "경험칙의 경간 범위에 해당하는지 표시. 내력은 별도 검토.",
                  "type": "boolean"
                },
                "name": {
                  "type": "string"
                },
                "render_material_ids": {
                  "description": "model_01-assign_material tool에 전달할 재료 ID 후보.",
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "structural_material": {
                  "type": "string"
                },
                "system_id": {
                  "description": "유형 조회의 construction_system 또는 model_01-assign_material tool의 construction_reference.id로 사용.",
                  "type": "string"
                }
              },
              "required": [
                "system_id"
              ],
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

**beyond · RhinoTerminal**

```txt
건축 유형 조회. 서사·선례·관련 구법은 `field_groups: ["narrative"]`로 요청한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "construction_system": {
      "description": "research_01-get_construction_guidance tool의 `system_id`.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 5,
      "description": "기본값 5",
      "type": "integer"
    },
    "query": {
      "description": "예: `courtyard`, `skyscraper`, `timber hall`.",
      "type": "string"
    },
    "structure_type": {
      "description": "research_01-get_construction_guidance tool과 같은 구조 유형.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "construction_system": {
      "description": "research_01-get_construction_guidance tool의 `system_id`.",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "limit": {
      "default": 5,
      "description": "기본값 5",
      "type": "integer"
    },
    "query": {
      "description": "예: `courtyard`, `skyscraper`, `timber hall`.",
      "type": "string"
    },
    "structure_type": {
      "description": "research_01-get_construction_guidance tool과 같은 구조 유형.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                "precedents": {
                  "items": {
                    "properties": {
                      "date": {
                        "type": "string"
                      },
                      "name": {
                        "type": "string"
                      },
                      "place": {
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "type": "array"
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
              "required": [
                "typology_id"
              ],
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

**beyond · RhinoTerminal**

```txt
건축 자료 출처의 제목·태그·형식 검색. URL과 이용 조건은 `field_groups: ["all"]`로 요청한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "query": {
      "description": "빈 문자열로 출처 목록 조회. 검색 가능한 단어가 없으면 `invalid_query`.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "rules",
              "narrative",
              "source",
              "metadata",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "query": {
      "description": "빈 문자열로 출처 목록 조회. 검색 가능한 단어가 없으면 `invalid_query`.",
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "error_code": {
      "type": "string"
    },
    "message": {
      "type": "string"
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
          "tags": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "terms_url": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "title": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "required": [
          "source_id"
        ],
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

**beyond · RhinoTerminal**

```txt
Rhino 객체를 Scene에 추가하거나 해당 Scene에서 제외한 Holon 구성원을 복원
응답의 인덱스는 object_ids에서 0부터 센다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "scene_07-list tool에서 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "object_ids",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
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
      "description": "scene_07-list tool에서 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "object_ids",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "already_present_indices": {
            "description": "Holon을 통해 이미 포함된 객체도 해당",
            "items": {
              "type": "integer"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "failed_indices": {
            "items": {
              "type": "integer"
            },
            "type": "array"
          },
          "message": {
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

**beyond · RhinoTerminal**

```txt
설계 영역이나 프로그램, 상황을 나타내는 Scene 생성
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "file_name": {
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외",
      "type": "string"
    },
    "name": {
      "description": "빈 이름은 Untitled scene으로 저장.",
      "type": "string"
    },
    "units": {
      "description": "기본 mm",
      "enum": [
        "mm",
        "cm",
        "m",
        "in",
        "ft"
      ],
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "file_name": {
      "description": "context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외",
      "type": "string"
    },
    "name": {
      "description": "빈 이름은 Untitled scene으로 저장.",
      "type": "string"
    },
    "units": {
      "description": "기본 mm",
      "enum": [
        "mm",
        "cm",
        "m",
        "in",
        "ft"
      ],
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "scene": {
            "properties": {
              "revision": {
                "type": "integer"
              },
              "scene_id": {
                "type": "string"
              }
            },
            "required": [
              "scene_id",
              "revision"
            ],
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

**beyond · RhinoTerminal**

```txt
Holon의 유효 구성원을 선택·격리·확대한다. 격리 해제는 view_change.restore_visibility_command를 쓴다. 카메라와 선택은 별도로 복원한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
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
    "connection_id",
    "holon_ids"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "camera_target": {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "frustum": {
                    "description": "left, right, bottom, top, near, far",
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
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "camera_target": {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "frustum": {
                    "description": "left, right, bottom, top, near, far",
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
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  },
                  "min": {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 3,
                    "minItems": 3,
                    "type": "array"
                  }
                },
                "required": [
                  "min",
                  "max"
                ],
                "type": "object"
              },
              "target_bounds_error": {
                "type": "string"
              },
              "target_count": {
                "type": "integer"
              },
              "zoom_bounding_box": {
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "zoom_extents_selected": {
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ]
              }
            },
            "type": "object"
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
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "null이면 뷰 변경 적용을 확인하지 못한 상태."
          },
          "requires_reconciliation": {
            "description": "true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.",
            "type": "boolean"
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
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "isolated": {
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "restore_visibility_command": {
                "description": "격리 가시성만 복구. 카메라와 선택은 별도로 확인.",
                "type": "string"
              },
              "selection_changed": {
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
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
                "anyOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "선택 확대 또는 대체 경계 확대를 완료하면 true."
              }
            },
            "type": "object"
          },
          "viewport_id": {
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


### 68. scene_04-get

**beyond · RhinoTerminal**

```txt
저장된 Scene과 Holon·객체 수를 조회한다. 현재 Rhino 구성원은 scene_06-get_objects tool에서 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "scene": {
            "properties": {
              "direct_objects": {
                "type": "integer"
              },
              "file_name": {
                "type": "string"
              },
              "holons": {
                "type": "integer"
              },
              "name": {
                "type": "string"
              },
              "objects": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "직접 등록 또는 제외 override가 있으면 저장된 정보만으로 수를 확정하기 어려워 null 반환"
              },
              "revision": {
                "type": "integer"
              },
              "units": {
                "enum": [
                  "mm",
                  "cm",
                  "m",
                  "in",
                  "ft"
                ],
                "type": "string"
              },
              "updated_at": {
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

**beyond · RhinoTerminal**

```txt
Holon의 등록 정보와 구성원 조회. live=true로 현재 Rhino 상태를 등록 정보와 대조하고 requires_sync로 동기화 필요 여부를 확인. recursive=true는 Rhino 블록 정의 경계는 유지하며 자손 Holon을 확장. include_ids=true일 때도 입력한 holon_id는 요약에서 생략.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "references",
              "geometry",
              "scope",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "holon_id": {
      "description": "include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID",
      "type": "string"
    },
    "include_ids": {
      "description": "요청한 필드 그룹에 해당하는 ID만 포함",
      "type": "boolean"
    },
    "live": {
      "type": "boolean"
    },
    "recursive": {
      "type": "boolean"
    }
  },
  "required": [
    "connection_id",
    "holon_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "references",
              "geometry",
              "scope",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "holon_id": {
      "description": "include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID",
      "type": "string"
    },
    "include_ids": {
      "description": "요청한 필드 그룹에 해당하는 ID만 포함",
      "type": "boolean"
    },
    "live": {
      "type": "boolean"
    },
    "recursive": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
              "bounds_mm": {
                "anyOf": [
                  {
                    "items": {
                      "type": "number"
                    },
                    "maxItems": 6,
                    "minItems": 6,
                    "type": "array"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "`geometry` 또는 `all`에서 반환하는 유효 구성원의 경계."
              },
              "child_holon_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "created_at": {
                "description": "`audit` 또는 `all`에서 반환.",
                "type": "string"
              },
              "effective_object_count": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
              },
              "effective_objects": {
                "items": {
                  "properties": {
                    "bounds_mm": {
                      "items": {
                        "type": "number"
                      },
                      "maxItems": 6,
                      "minItems": 6,
                      "type": "array"
                    },
                    "holon_id": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "object_type": {
                      "type": "string"
                    },
                    "rhino_guid": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "file_name": {
                "description": "`scope` 또는 `all`에서 반환.",
                "type": "string"
              },
              "live_verified": {
                "type": "boolean"
              },
              "model_path": {
                "type": "string"
              },
              "name": {
                "type": "string"
              },
              "object_count": {
                "type": "integer"
              },
              "objects": {
                "items": {
                  "properties": {
                    "bounds_mm": {
                      "items": {
                        "type": "number"
                      },
                      "maxItems": 6,
                      "minItems": 6,
                      "type": "array"
                    },
                    "holon_id": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "object_type": {
                      "type": "string"
                    },
                    "rhino_guid": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                },
                "type": "array"
              },
              "parent_holon_id": {
                "anyOf": [
                  {
                    "type": "string"
                  },
                  {
                    "type": "null"
                  }
                ],
                "description": "`references` 또는 `all`과 include_ids=true에서 반환."
              },
              "requires_sync": {
                "type": "boolean"
              },
              "rhino_group_id": {
                "type": "string"
              },
              "scene_ids": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "updated_at": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "message": {
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

**beyond · RhinoTerminal**

```txt
현재 Rhino 문서에서 Scene의 직접 객체와 Holon 구성원 조회. Scene에서 제외한 구성원은 생략.
페이지 기본값은 limit=50, offset=0이며 limit은 1~200이다. truncated이면 같은 조건에서 반환한 항목 수만큼 offset을 늘린다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "description": "지정한 경로가 연결 문서와 일치해야 함",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "model_path": {
            "type": "string"
          },
          "objects": {
            "items": {
              "properties": {
                "bounds_mm": {
                  "items": {
                    "type": "number"
                  },
                  "maxItems": 6,
                  "minItems": 6,
                  "type": "array"
                },
                "holon_id": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                },
                "object_type": {
                  "type": "string"
                },
                "rhino_guid": {
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


### 71. scene_07-list

**beyond · RhinoTerminal**

```txt
공유 프로젝트 DB의 Scene 목록 조회. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 조회.
페이지 기본값은 limit=50, offset=0이며 limit은 1~200이다. truncated이면 같은 조건에서 반환한 항목 수만큼 offset을 늘린다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "file_name": {
      "description": "확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회",
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "name": {
      "description": "대소문자를 구분하지 않는 부분 검색",
      "type": "string"
    },
    "offset": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "scope",
              "state",
              "geometry",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "file_name": {
      "description": "확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회",
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "name": {
      "description": "대소문자를 구분하지 않는 부분 검색",
      "type": "string"
    },
    "offset": {
      "type": "integer"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "scenes": {
            "items": {
              "properties": {
                "created_at": {
                  "type": "string"
                },
                "file_name": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                },
                "revision": {
                  "type": "integer"
                },
                "scene_id": {
                  "type": "string"
                },
                "units": {
                  "enum": [
                    "mm",
                    "cm",
                    "m",
                    "in",
                    "ft"
                  ],
                  "type": "string"
                },
                "updated_at": {
                  "type": "string"
                }
              },
              "required": [
                "scene_id"
              ],
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


### 72. scene_08-list_holons

**beyond · RhinoTerminal**

```txt
모델에서 저장된 Holon 등록 목록 조회. Scene을 지정하면 연결된 Holon을, 생략하면 기본으로 최상위 Holon을 조회. recursive=true는 자손을 포함하며 이 자손은 Scene에 직접 등록되지 않았을 수 있다. 현재 Rhino 구성원은 scene_05-get_holon tool에서 live=true로 조회.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "관리형 세션에서 생략하면 연결된 모델 기준",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "references",
              "geometry",
              "scope",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "recursive": {
      "type": "boolean"
    },
    "scene_id": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "description": "관리형 세션에서 생략하면 연결된 모델 기준",
      "type": "string"
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "enum": [
              "references",
              "geometry",
              "scope",
              "audit",
              "all"
            ],
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ]
    },
    "include_ids": {
      "type": "boolean"
    },
    "recursive": {
      "type": "boolean"
    },
    "scene_id": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
              "properties": {
                "availability": {
                  "type": "string"
                },
                "bounds_mm": {
                  "anyOf": [
                    {
                      "items": {
                        "type": "number"
                      },
                      "maxItems": 6,
                      "minItems": 6,
                      "type": "array"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "description": "`geometry` 또는 `all`에서 반환하는 유효 구성원의 경계."
                },
                "child_holon_ids": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "created_at": {
                  "description": "`audit` 또는 `all`에서 반환.",
                  "type": "string"
                },
                "effective_object_count": {
                  "anyOf": [
                    {
                      "type": "integer"
                    },
                    {
                      "type": "null"
                    }
                  ]
                },
                "file_name": {
                  "description": "`scope` 또는 `all`에서 반환.",
                  "type": "string"
                },
                "holon_id": {
                  "type": "string"
                },
                "model_path": {
                  "type": "string"
                },
                "name": {
                  "type": "string"
                },
                "object_count": {
                  "type": "integer"
                },
                "parent_holon_id": {
                  "anyOf": [
                    {
                      "type": "string"
                    },
                    {
                      "type": "null"
                    }
                  ],
                  "description": "`references` 또는 `all`과 include_ids=true에서 반환."
                },
                "requires_sync": {
                  "type": "boolean"
                },
                "rhino_group_id": {
                  "type": "string"
                },
                "scene_ids": {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                "updated_at": {
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


### 73. scene_09-remove_holon

**beyond · RhinoTerminal**

```txt
Holon 등록 해제. Rhino 형상과 그룹은 보존. 변경 여부가 불확실하면 scene_11-sync_holon tool로 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "holon_id": {
      "description": "이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "holon_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "expected_model_path": {
            "type": "string"
          },
          "holon_id": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "requires_reconciliation": {
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


### 74. scene_10-remove_objects

**beyond · RhinoTerminal**

```txt
객체를 Scene에서 제외. Rhino 형상과 Holon 그룹은 보존.
응답의 인덱스는 object_ids에서 0부터 센다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
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
      "description": "scene_07-list tool에서 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "object_ids",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
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
      "description": "scene_07-list tool에서 조회한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "object_ids",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "result": {
      "contentMediaType": "application/json",
      "contentSchema": {
        "properties": {
          "already_absent_indices": {
            "items": {
              "type": "integer"
            },
            "type": "array"
          },
          "error_code": {
            "type": "string"
          },
          "failed_indices": {
            "items": {
              "type": "integer"
            },
            "type": "array"
          },
          "message": {
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

**beyond · RhinoTerminal**

```txt
현재 Rhino 구성원으로 Holon 등록 정보를 갱신한다. holon_ids 또는 scene_id로 대상을 선택한다. 둘 다 생략하면 연결 모델 전체를 확인한다. holon_ids는 서로 다른 ID 1~64개다. 한 Holon의 그룹 일치를 확인하려면 holon_id와 rhino_group_id를 함께 보낸다. Scene 범위에 부모 Holon이 빠져 있으면 응답의 next_action을 따른다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "holon_id": false,
        "rhino_group_id": false,
        "scene_id": false
      },
      "required": [
        "holon_ids"
      ]
    },
    {
      "properties": {
        "holon_ids": false,
        "scene_id": false
      },
      "required": [
        "holon_id"
      ]
    },
    {
      "properties": {
        "holon_id": false,
        "holon_ids": false,
        "rhino_group_id": false
      }
    }
  ],
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "type": "string"
    },
    "holon_ids": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "rhino_group_id": {
      "type": "string"
    },
    "scene_id": {
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "anyOf": [
    {
      "properties": {
        "holon_id": false,
        "rhino_group_id": false,
        "scene_id": false
      },
      "required": [
        "holon_ids"
      ]
    },
    {
      "properties": {
        "holon_ids": false,
        "scene_id": false
      },
      "required": [
        "holon_id"
      ]
    },
    {
      "properties": {
        "holon_id": false,
        "holon_ids": false,
        "rhino_group_id": false
      }
    }
  ],
  "properties": {
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
      "type": "string"
    },
    "holon_ids": {
      "items": {
        "type": "string"
      },
      "type": "array"
    },
    "rhino_group_id": {
      "type": "string"
    },
    "scene_id": {
      "type": "string"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "missing_holon_ids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "missing_parent_holon_ids": {
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "mutation_applied": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ]
          },
          "next_action": {
            "type": "string"
          },
          "problems": {
            "description": "문제 항목과 무관한 유효 등록은 함께 갱신될 수 있음",
            "items": {},
            "type": "array"
          },
          "scene_revisions": {
            "additionalProperties": {
              "type": "integer"
            },
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

**beyond · RhinoTerminal**

```txt
Scene의 프로젝트 파일 연결 변경 또는 해제
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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
      "description": "빈 문자열은 연결 해제. 생략하거나 null이면 기존 파일 연결을 유지한다."
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
      "type": "string"
    }
  },
  "required": [
    "connection_id",
    "scene_id"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "빈 문자열은 연결 해제. 생략하거나 null이면 기존 파일 연결을 유지한다."
    },
    "scene_id": {
      "description": "scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID",
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "scene": {
            "description": "파일 연결이 바뀌면 증가",
            "properties": {
              "revision": {
                "type": "integer"
              }
            },
            "required": [
              "revision"
            ],
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

**beyond · RhinoTerminal**

```txt
물리적 요소와 관계를 Holon으로 등록하거나 갱신한다. 변경 여부가 불확실하면 scene_11-sync_holon tool로 확인한다.
```

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
      "description": "빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
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
      "description": "최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용"
    },
    "rhino_group_id": {
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
      "description": "새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지"
    }
  },
  "required": [
    "connection_id",
    "name"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

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
      "description": "빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지"
    },
    "expected_model_path": {
      "description": "생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.",
      "type": "string"
    },
    "holon_id": {
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
      "description": "최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용"
    },
    "rhino_group_id": {
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "expected_model_path": {
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
              },
              "rhino_group_id": {
                "type": "string"
              }
            },
            "type": "object"
          },
          "holon_id": {
            "type": "string"
          },
          "message": {
            "type": "string"
          },
          "requires_reconciliation": {
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


### 78. script_01-run_project_python

**beyond · RhinoTerminal**

```txt
선택한 Plan·Loop 폴더에서 Python을 실행한다. 상대 경로로 산출물을 쓰고 JSON 결과는 result에 할당한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "description": "동기식 Python. doc과 scriptcontext.doc은 연결 문서. 상대 경로는 산출물 폴더 기준.",
      "type": "string"
    },
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "timeout_seconds": {
      "description": "1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.",
      "maximum": 600,
      "minimum": 1,
      "type": "integer"
    }
  },
  "required": [
    "connection_id",
    "code"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "description": "동기식 Python. doc과 scriptcontext.doc은 연결 문서. 상대 경로는 산출물 폴더 기준.",
      "type": "string"
    },
    "timeout_seconds": {
      "description": "1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.",
      "maximum": 600,
      "minimum": 1,
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "artifact_dir": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "completed": {
      "type": "boolean"
    },
    "completion_state": {
      "type": "string"
    },
    "connection_state": {
      "type": "string"
    },
    "diagnostics_truncated": {
      "type": "boolean"
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
    "pending": {
      "type": "boolean"
    },
    "request_id": {
      "type": "string"
    },
    "result": {},
    "result_bytes": {
      "type": "integer"
    },
    "result_display_error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "result_error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "result_file": {
      "type": "string"
    },
    "result_page": {
      "properties": {
        "available_fields": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "metadata_truncated": {
          "type": "boolean"
        },
        "pages": {
          "additionalProperties": {
            "properties": {
              "next_offset": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
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
    "result_sha256": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "timed_out": {
      "type": "boolean"
    },
    "uncertain": {
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>


### 79. script_02-run_rhino

**beyond · RhinoTerminal**

```txt
RhinoCode에서 스크립트나 명령을 실행한다. 완료가 불확실하면 request_id로 실행 기록과 모델 상태를 확인한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "language": {
      "default": "python",
      "description": "기본값 \"python\" (Python 3)",
      "enum": [
        "python",
        "python2",
        "csharp",
        "csharp-script",
        "command"
      ],
      "type": "string"
    },
    "script": {
      "description": "Python은 result에 JSON 호환 값, C# 문장 본문은 result_json에 JSON을 할당. doc은 연결 문서. 명령 매크로는 !·Pause·대화상자 없이 종료해야 한다.",
      "type": "string"
    },
    "timeout_seconds": {
      "description": "1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.",
      "maximum": 600,
      "minimum": 1,
      "type": "integer"
    }
  },
  "required": [
    "connection_id",
    "script"
  ],
  "type": "object"
}
```

</details>

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "language": {
      "default": "python",
      "description": "기본값 \"python\" (Python 3)",
      "enum": [
        "python",
        "python2",
        "csharp",
        "csharp-script",
        "command"
      ],
      "type": "string"
    },
    "script": {
      "description": "Python은 result에 JSON 호환 값, C# 문장 본문은 result_json에 JSON을 할당. doc은 연결 문서. 명령 매크로는 !·Pause·대화상자 없이 종료해야 한다.",
      "type": "string"
    },
    "timeout_seconds": {
      "description": "1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.",
      "maximum": 600,
      "minimum": 1,
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

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
            "type": "string"
          },
          "connection_state": {
            "type": "string"
          },
          "diagnostics_truncated": {
            "type": "boolean"
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
          "pending": {
            "type": "boolean"
          },
          "request_id": {
            "type": "string"
          },
          "result": {},
          "result_bytes": {
            "type": "integer"
          },
          "result_display_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "result_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ]
          },
          "result_file": {
            "type": "string"
          },
          "result_page": {
            "properties": {
              "available_fields": {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              "metadata_truncated": {
                "type": "boolean"
              },
              "pages": {
                "additionalProperties": {
                  "properties": {
                    "next_offset": {
                      "anyOf": [
                        {
                          "type": "integer"
                        },
                        {
                          "type": "null"
                        }
                      ]
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
          "result_sha256": {
            "type": "string"
          },
          "status": {
            "type": "string"
          },
          "timed_out": {
            "type": "boolean"
          },
          "uncertain": {
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

**beyond · RhinoTerminal**

```txt
실행 상태·결과·로그를 조회한다. 결과의 배열은 항목, 문자열은 문자, 로그는 바이트 단위로 페이지를 읽는다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
      "pattern": "^[0-9a-f]{32}$",
      "type": "string"
    },
    "include_diagnostics": {
      "description": "정상 완료에서도 CLI·Undo·호출 식별 근거를 diagnostics에 포함.",
      "type": "boolean"
    },
    "include_ids": {
      "default": true,
      "description": "기본값 true",
      "type": "boolean"
    },
    "include_result": {
      "default": true,
      "description": "기본값 true",
      "type": "boolean"
    },
    "include_stdout": {
      "description": "stdout·stderr와 CLI 로그 포함",
      "type": "boolean"
    },
    "limit": {
      "default": 100,
      "description": "결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용 · 기본값 100",
      "maximum": 1000,
      "minimum": 1,
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "기본값 0",
      "minimum": 0,
      "type": "integer"
    },
    "request_id": {
      "description": "생략 시 현재 연결의 최근 실행. 시간 초과 후에는 반환된 ID를 지정.",
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "include_diagnostics": {
      "description": "정상 완료에서도 CLI·Undo·호출 식별 근거를 diagnostics에 포함.",
      "type": "boolean"
    },
    "include_ids": {
      "default": true,
      "description": "기본값 true",
      "type": "boolean"
    },
    "include_result": {
      "default": true,
      "description": "기본값 true",
      "type": "boolean"
    },
    "include_stdout": {
      "description": "stdout·stderr와 CLI 로그 포함",
      "type": "boolean"
    },
    "limit": {
      "default": 100,
      "description": "결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용 · 기본값 100",
      "maximum": 1000,
      "minimum": 1,
      "type": "integer"
    },
    "offset": {
      "default": 0,
      "description": "기본값 0",
      "minimum": 0,
      "type": "integer"
    },
    "request_id": {
      "description": "생략 시 현재 연결의 최근 실행. 시간 초과 후에는 반환된 ID를 지정.",
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
      "description": "객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키"
    }
  },
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

```json
{
  "properties": {
    "cleanup_errors": {
      "items": {},
      "type": "array"
    },
    "cli_stderr": {
      "type": "string"
    },
    "cli_stderr_page": {
      "properties": {
        "next_offset": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "retained_bytes": {
          "type": "integer"
        },
        "returned_bytes": {
          "type": "integer"
        }
      },
      "type": "object"
    },
    "cli_stdout": {
      "type": "string"
    },
    "cli_stdout_page": {
      "properties": {
        "next_offset": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "retained_bytes": {
          "type": "integer"
        },
        "returned_bytes": {
          "type": "integer"
        }
      },
      "type": "object"
    },
    "completed": {
      "type": "boolean"
    },
    "completion_state": {
      "type": "string"
    },
    "connection_state": {
      "type": "string"
    },
    "diagnostics": {
      "additionalProperties": true,
      "description": "상세 요청 또는 실패·미확정 실행의 근거. 요청한 로그가 잘리거나 읽히지 않은 경우와 연결 종료 후 조회한 실행의 Rhino 식별 정보도 포함한다.",
      "type": "object"
    },
    "diagnostics_truncated": {
      "type": "boolean"
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
    "native_completed": {
      "type": "boolean"
    },
    "pending": {
      "type": "boolean"
    },
    "recovery_only": {
      "type": "boolean"
    },
    "request_id": {
      "type": "string"
    },
    "requires_reconnect": {
      "type": "boolean"
    },
    "result": {},
    "result_available": {
      "description": "include_result=false일 때 보관된 결과 유무.",
      "type": "boolean"
    },
    "result_bytes": {
      "type": "integer"
    },
    "result_display_error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "result_error": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ]
    },
    "result_file": {
      "type": "string"
    },
    "result_page": {
      "properties": {
        "available_fields": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "metadata_truncated": {
          "type": "boolean"
        },
        "pages": {
          "additionalProperties": {
            "properties": {
              "next_offset": {
                "anyOf": [
                  {
                    "type": "integer"
                  },
                  {
                    "type": "null"
                  }
                ]
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
    "result_sha256": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "stderr": {
      "type": "string"
    },
    "stderr_page": {
      "properties": {
        "next_offset": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "retained_bytes": {
          "type": "integer"
        },
        "returned_bytes": {
          "type": "integer"
        }
      },
      "type": "object"
    },
    "stdout": {
      "type": "string"
    },
    "stdout_page": {
      "properties": {
        "next_offset": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "null"
            }
          ]
        },
        "retained_bytes": {
          "type": "integer"
        },
        "returned_bytes": {
          "type": "integer"
        }
      },
      "type": "object"
    },
    "timed_out": {
      "type": "boolean"
    },
    "uncertain": {
      "type": "boolean"
    }
  },
  "type": "object"
}
```

</details>


### 81. script_04-save_document

**beyond · RhinoTerminal**

```txt
사용자가 영구 저장을 요청하면 연결 문서 전체를 기존 .3dm 경로에 저장한다.
```

<details><summary>beyond 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "maxLength": 32,
      "minLength": 32,
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

<details><summary>RhinoTerminal 입력 스키마</summary>

```json
{
  "additionalProperties": false,
  "properties": {},
  "type": "object"
}
```

</details>

<details><summary>beyond · RhinoTerminal 출력 스키마</summary>

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
          "requires_reconciliation": {
            "type": "boolean"
          },
          "saved": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "description": "저장이 미확정이면 null이다. 재호출 전 문서 상태를 확인한다."
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

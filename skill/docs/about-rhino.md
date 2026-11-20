# Rhino의 Group과 Block

## Group

- 여러 객체를 함께 선택하고 다루는 묶음이다. 구성 객체는 각각 별개의 객체로 남는다.
- Group은 다른 group과 block instance를 포함할 수 있다. 한 객체가 여러 group에 속할 수도 있으므로, 중첩 관계를 단일 부모를 가진 트리로 가정하지 않는다.
- Group 자체는 변경 사항을 복사본에 전파하는 공유 정의가 아니다.

## Block

- Block은 형상과 구성을 담은 **definition**과 이를 참조하는 **instance**로 이루어진다. Instance마다 위치·회전·축척은 다를 수 있다.
- 같은 definition을 공유하는 instance는 definition을 수정하면 함께 바뀐다. 한 배치만 수정하려면 먼저 공유 관계와 영향을 확인하고 definition을 분리한다. Rhino 8의 `CreateUniqueBlock`을 사용할 수 있다.
- Definition 안에 다른 block instance를 중첩할 수 있다. Block instance를 group으로 묶거나 그 group을 복사해도 block의 definition 공유 관계는 유지된다.
- 따라서 **함께 선택되는 범위와 변경이 전파되는 범위는 다르다.** Definition을 편집하기 전에 다른 instance와 중첩된 구성에 미칠 영향을 확인한다.

## Block 안의 Group

BlockEditNew에서는 block 안의 중첩 group을 저장할 수 없다. Rhino 8에서 저장 시 `Cannot save nested group in block` 경고가 발생했다. 기존 group이 보이더라도 편집 후 중첩 구조가 유지된다고 가정하지 않는다.

## Block 편집과 객체 ID

- 편집할 때 대상이 **instance**, **공유 definition의 구성원**, 또는 **중첩된 구성원** 중 무엇인지 구분한다.
- Instance의 ID, definition 내부 객체의 ID, 편집기가 작업 대상으로 노출하는 ID는 서로 다른 맥락의 식별자다. 편집 진입·완료, 저장, 멤버 교체나 재구성 뒤에는 현재 맥락에서 대상과 ID를 다시 확인한다. ID가 매번 바뀐다는 뜻은 아니다.
- Definition 내부 경로와 누적 변환은 대상의 구성과 배치 위치를 파악하는 데 쓰인다. 경로가 맞더라도 편집기가 그 객체를 현재 편집 대상으로 소유하는지, 변경할 수 있는지는 별도로 확인한다.
- Almond의 중첩 block 영향 조회는 읽기 전용이다. 결과가 잘리거나 불완전하면 다른 배치에 영향이 없다고 판단하지 않는다.
- `BlockEditNew`의 편집 맥락과 ID 노출 방식은 Almond와 해당 편집기 버전의 지원 범위에 따라 확인한다. 표준 Rhino BlockEdit의 동작을 그대로 가정하지 않는다.

## 작업에 활용하기

반복해서 같은 형상을 공유할 문·창호·가구 등은 기존 definition의 형상과 규격을 확인하고 재사용한다. 함께 선택하거나 구성 관계를 다룰 때는 group을 활용한다. 유용한 group이나 block을 의미 등록이 아니라는 이유로 해체하거나 같은 묶음을 중복 생성하지 않는다.

개별 부재를 고치는지 공유 definition을 고치는지 구분하고, 변경 후 접합과 영향을 받는 상위 구성·다른 배치를 확인한다. 중첩 편집 단계 밖의 선택·표시 상태는 임의로 재설정하지 않는다. 묶음과 형상의 유효성만으로 공간적·구축적 적합성이 보장되는 것은 아니다.

## 참고

- Rhino 8: [Group](https://docs.mcneel.com/rhino/8/help/en-us/commands/group.htm), [Block](https://docs.mcneel.com/rhino/8/help/en-us/commands/block.htm), [객체의 group 목록](https://developer.rhino3d.com/api/rhinocommon/rhino.docobjects.objectattributes/getgrouplist)
- Almond 편집 맥락은 현재 `inspect_01-analyze_nested_blocks`와 관련 편집 도구의 설명을 따른다.

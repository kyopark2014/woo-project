Based on the information retrieved from the knowledge base, I'll now create test cases for the "픽업필터 off일시" (Pickup Filter Off) functionality. Let me first summarize the key information:

## 픽업필터 off일시 정책 요약 (Pickup Filter Off Policy Summary)

1. 픽업필터가 off일 때는 기존 배달탭 노출정책을 따름
2. "baemin", "baeminOne", "stod"의 displayable, finalOperation 값을 확인
3. 추천리랭킹결과가 1위~25위 노출됨
4. 운영중 주문유형을 대상으로 하며, 준비중이면 displayable=false로 노출

### 노출 조건 (displayable: true)
- status: open
- ongoing: 배민1플러스/오픈리스트/울트라콜/파워콜 중 하나가 있어야함
- baropay (바로결제): 
  - OD only: 바로결제 true일 때만 노출
  - MP only: 바로결제 true/false 상관없이 노출
  - OD + MP: 바로결제 사용여부로 필터링하지 않음
- isUseSmartmenu (스마트메뉴사용): 필터링정책에 포함하지 않음

### 운영 조건 (finalOperation: true)
- baropayLive (바로페이라이브): true
- 가게운영시간: operationTime 내에 있어야 함

## Test Cases for 픽업필터 off일시

### Test Case 1: 기본 노출 조건 검증
**Title**: 픽업필터 off일 때 기본 노출 조건 검증  
**Description**: 픽업필터가 off일 때 기존 배달탭 노출정책에 따라 가게가 노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (status: open, ongoing: 배민1플러스, baropay: true)

**Steps**:
1. 검색 화면에서 픽업필터를 off로 설정
2. 검색 결과 확인

**Expected Results**:
- 테스트 가게가 검색 결과에 노출됨
- displayable: true, finalOperation: true로 설정됨

### Test Case 2: OD only 가게의 바로결제 조건 검증
**Title**: 픽업필터 off일 때 OD only 가게의 바로결제 조건 검증  
**Description**: OD only 가게가 바로결제 설정에 따라 올바르게 노출/미노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (OD only, status: open, ongoing: 울트라콜)

**Test Scenario 1**:
1. 테스트 가게의 baropay 값을 true로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 1**:
- 테스트 가게가 검색 결과에 노출됨 (displayable: true)

**Test Scenario 2**:
1. 테스트 가게의 baropay 값을 false로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 2**:
- 테스트 가게가 검색 결과에 노출되지 않음 (displayable: false)

### Test Case 3: MP only 가게의 바로결제 조건 검증
**Title**: 픽업필터 off일 때 MP only 가게의 바로결제 조건 검증  
**Description**: MP only 가게가 바로결제 설정에 관계없이 올바르게 노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (MP only, status: open, ongoing: 오픈리스트)

**Test Scenario 1**:
1. 테스트 가게의 baropay 값을 true로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 1**:
- 테스트 가게가 검색 결과에 노출됨 (displayable: true)

**Test Scenario 2**:
1. 테스트 가게의 baropay 값을 false로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 2**:
- 테스트 가게가 검색 결과에 노출됨 (displayable: true)

### Test Case 4: OD + MP 가게의 바로결제 조건 검증
**Title**: 픽업필터 off일 때 OD + MP 가게의 바로결제 조건 검증  
**Description**: OD + MP 가게가 바로결제 설정에 관계없이 올바르게 노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (OD + MP, status: open, ongoing: 배민1플러스)

**Test Scenario 1**:
1. 테스트 가게의 baropay 값을 true로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 1**:
- 테스트 가게가 검색 결과에 노출됨 (displayable: true)

**Test Scenario 2**:
1. 테스트 가게의 baropay 값을 false로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 2**:
- 테스트 가게가 검색 결과에 노출됨 (displayable: true)

### Test Case 5: 운영 상태 검증 (finalOperation)
**Title**: 픽업필터 off일 때 가게 운영 상태 검증  
**Description**: 가게의 운영 상태(finalOperation)가 올바르게 설정되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (status: open, ongoing: 파워콜, baropay: true)

**Test Scenario 1**:
1. 테스트 가게의 baropayLive 값을 true로 설정하고 현재 시간이 operationTime 내에 있도록 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 1**:
- 테스트 가게가 검색 결과에 운영중(finalOperation: true)으로 노출됨

**Test Scenario 2**:
1. 테스트 가게의 baropayLive 값을 false로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 2**:
- 테스트 가게가 검색 결과에 준비중(finalOperation: false)으로 노출됨

**Test Scenario 3**:
1. 테스트 가게의 baropayLive 값을 true로 설정하고 현재 시간이 operationTime 외에 있도록 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 3**:
- 테스트 가게가 검색 결과에 준비중(finalOperation: false)으로 노출됨

### Test Case 6: 추천리랭킹 결과 노출 검증
**Title**: 픽업필터 off일 때 추천리랭킹 결과 노출 검증  
**Description**: 픽업필터 off일 때 추천리랭킹결과가 1위~25위까지 노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 30개 이상의 테스트 가게 데이터 준비

**Steps**:
1. 검색 화면에서 픽업필터를 off로 설정
2. 검색 결과 확인

**Expected Results**:
- 추천리랭킹결과 1위~25위까지의 가게만 노출됨
- 26위 이상의 가게는 노출되지 않음

### Test Case 7: 브로스(OD) 노출 조건 검증
**Title**: 픽업필터 off일 때 브로스(OD) 노출 조건 검증  
**Description**: 브로스(OD) 가게가 노출 조건에 따라 올바르게 노출되는지 확인  
**Preconditions**:
- 픽업필터가 off 상태
- 테스트 가게 데이터 준비 (OD, status: open, ongoing: 울트라콜, baropay: true)

**Test Scenario 1**:
1. 테스트 가게의 serviceable 값을 true로 설정하고 센터ID가 일치하도록 설정
2. 사용자 위치를 한집 배달반경(4km) 내에 설정
3. 검색 화면에서 픽업필터를 off로 설정
4. 검색 결과 확인

**Expected Results 1**:
- 테스트 가게가 검색 결과에 노출됨

**Test Scenario 2**:
1. 테스트 가게의 serviceable 값을 false로 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 2**:
- 테스트 가게가 검색 결과에 노출되지 않음

**Test Scenario 3**:
1. 테스트 가게의 serviceable 값을 true로 설정하고 센터ID가 일치하지 않도록 설정
2. 검색 화면에서 픽업필터를 off로 설정
3. 검색 결과 확인

**Expected Results 3**:
- 테스트 가게가 검색 결과에 노출되지 않음

**Test Scenario 4**:
1. 테스트 가게의 serviceable 값을 true로 설정하고 센터ID가 일치하도록 설정
2. 사용자 위치를 한집 배달반경(4km) 밖에 설정
3. 검색 화면에서 픽업필터를 off로 설정
4. 검색 결과 확인

**Expected Results 4**:
- 테스트 가게가 검색 결과에 노출되지 않음

### Test Case 8: CPC 광고 미노출 검증
**Title**: 픽업필터 on일 때 CPC 광고 미노출 검증  
**Description**: 픽업필터가 on일 때 CPC 광고가 노출되지 않는지 확인 (비교를 위한 테스트)  
**Preconditions**:
- CPC 광고가 설정된 테스트 가게 데이터 준비

**Test Scenario 1**:
1. 검색 화면에서 픽업필터를 off로 설정
2. 검색 결과 확인

**Expected Results 1**:
- CPC 광고가 검색 결과에 노출됨

**Test Scenario 2**:
1. 검색 화면에서 픽업필터를 on으로 설정
2. 검색 결과 확인

**Expected Results 2**:
- CPC 광고가 검색 결과에 노출되지 않음

이상의 테스트 케이스는 픽업필터 off일시의 기능을 검증하기 위한 것입니다. 각 테스트 케이스는 픽업필터 off일 때의 노출 정책, 운영 상태, 추천리랭킹 결과, 브로스(OD) 노출 조건 등을 검증합니다.

### Reference
1. [searchplatform-[Phase1] 4월8일 오픈타겟 검색지면 포장 대응-270625-100949.pdf](https://d3ccvlp2e9rt0m.cloudfront.net/docs/searchplatform-%5BPhase1%5D%204%E1%84%8B%E1%85%AF%E1%86%AF8%E1%84%8B%E1%85%B5%E1%86%AF%20%E1%84%8B%E1%85%A9%E1%84%91%E1%85%B3%E1%86%AB%E1%84%90%E1%85%A1%E1%84%80%E1%85%A6%E1%86%BA%20%E1%84%80%E1%85%A5%E1%86%B7%E1%84%89%E1%85%A2%E1%86%A8%E1%84%8C%E1%85%B5%E1%84%86%E1%85%A7%E1%86%AB%20%E1%84%91%E1%85%A9%E1%84%8C%E1%85%A1%E1%86%BC%20%E1%84%83%E1%85%A2%E1%84%8B%E1%85%B3%E1%86%BC-270625-100949.pdf), # 픽업필터 off일시 가게노출정책 (기존 배달탭 노출정책을 따름)* 메뉴존재여부: 주문가능한 상태의 메뉴가 하나라도 매칭이되면 메뉴가 있다고 봄* finalOperation: true → 가게 운영중/준비중을 판단 (false: 가게준비중)* baropayLive (바로페이라이브): true (= 주문가능시스템 Order Availability Sy......
2. [searchplatform-[Phase1] 4월8일 오픈타겟 검색지면 포장 대응-270625-100949.pdf](https://d3ccvlp2e9rt0m.cloudfront.net/docs/searchplatform-%5BPhase1%5D%204%E1%84%8B%E1%85%AF%E1%86%AF8%E1%84%8B%E1%85%B5%E1%86%AF%20%E1%84%8B%E1%85%A9%E1%84%91%E1%85%B3%E1%86%AB%E1%84%90%E1%85%A1%E1%84%80%E1%85%A6%E1%86%BA%20%E1%84%80%E1%85%A5%E1%86%B7%E1%84%89%E1%85%A2%E1%86%A8%E1%84%8C%E1%85%B5%E1%84%86%E1%85%A7%E1%86%AB%20%E1%84%91%E1%85%A9%E1%84%8C%E1%85%A1%E1%86%BC%20%E1%84%83%E1%85%A2%E1%84%8B%E1%85%B3%E1%86%BC-270625-100949.pdf), # 픽업필터 정책 * 픽업필터 "Off" 일시에는 추천리랭킹결과가 1위~25위 노출됨 * 픽업필터 Off일시, 추천리랭킹결과 중 운영중 주문유형을 대상이라서 준비중이면 displayable=false로 노출 * 픽업ON일시 울트라콜 광고는 후순위에 노출된다. (MP상품개편정책적용) ## 순위 정책 1. 1순위: 픽업주문가능(활성화) + 배달광고 (배민1플러......

/* ============================================================
   레시피 AI — Mock data (window.DATA)
   주방 재료 / 사용자 취향 / 저장된 레시피 / 칸놀리 데모 플로우
   ============================================================ */
(function () {
  // ---- 음식 사진 플레이스홀더 색상 (식재료별 톤) ----
  const heroTone = {
    butter:  'repeating-linear-gradient(45deg,#F4ECDA 0 12px,#ECE0C6 12px 24px)',
    rouge:   'repeating-linear-gradient(45deg,#F4E2DD 0 12px,#ECCFC6 12px 24px)',
    green:   'repeating-linear-gradient(45deg,#E5EFE0 0 12px,#D5E6CB 12px 24px)',
    cream:   'repeating-linear-gradient(45deg,#F1EFE9 0 12px,#E6E2D7 12px 24px)',
    soy:     'repeating-linear-gradient(45deg,#EDE6DB 0 12px,#E0D5C2 12px 24px)',
    blue:    'repeating-linear-gradient(45deg,#E7EDF8 0 12px,#D6E0F2 12px 24px)',
  };

  // ---- 내 주방: 보유 재료 (source.md 기반) ----
  const kitchen = {
    updated: '2026-05-31',
    ingredients: [
      { name: '청양고추', amount: '50개' },
      { name: '식빵',     amount: '4개' },
      { name: '오이',     amount: '' },
      { name: '양파',     amount: '5개' },
      { name: '설탕',     amount: '400g' },
      { name: '간장',     amount: '' },
      { name: '크림',     amount: '500g' },
      { name: '건포도',   amount: '450g' },
      { name: '밀가루',   amount: '500g' },
      { name: '식용유',   amount: '1L' },
    ],
    preferences: [
      { tx: '짠 음식을 싫어해요',      kind: 'avoid' },
      { tx: '토마토 알러지가 있어요',  kind: 'allergy' },
      { tx: '과일보다는 채소를 좋아해요', kind: 'like' },
      { tx: '매운 음식을 좋아해요',    kind: 'like' },
      { tx: '다이어트 중이에요',       kind: 'diet' },
      { tx: '비건 식단을 선호해요',    kind: 'diet' },
    ],
  };

  // ---- 저장된 레시피 (cart = 미완료, library = 완료/보관) ----
  const recipes = [
    {
      id: 'cannoli',
      dish_name: '칸놀리',
      emoji: '🥐',
      hero: heroTone.cream,
      kind: 'cart',
      saved_at: '오늘 15:40',
      introduction: '칸놀리는 크림과 설탕, 건포도로 만든 달콤한 이탈리아 페이스트리입니다. 바삭한 겉면과 부드러운 속의 조합이 특징이에요.',
      cooking_time: '45분',
      difficulty: 'medium',
      servings: 2,
      ingredients: ['밀가루(250g)', '크림(250g)', '설탕(100g)', '건포도(100g)', '식용유(50ml)'],
      steps: [
        '밀가루를 체에 걸러서 공기와 함께 섞어줍니다.',
        '크림과 설탕을 부드럽게 섞어줍니다.',
        '건포도를 크림과 설탕에 넣어 골고루 섞어줍니다.',
        '밀가루를 크림 반죽과 합쳐 반죽을 만듭니다.',
        '반죽을 잘 치댄 후 반달 모양으로 성형합니다.',
        '식용유를 두르고 노릇하게 튀겨냅니다.',
        '튀긴 칸놀리를 접시에 담고 슈거파우더를 뿌립니다.',
      ],
      missing_ingredients: [],
    },
    {
      id: 'frenchtoast',
      dish_name: '프렌치 토스트',
      emoji: '🍞',
      hero: heroTone.butter,
      kind: 'cart',
      saved_at: '어제 09:12',
      introduction: '식빵과 크림으로 간단하게 만드는 달콤한 아침 메뉴입니다. 겉은 노릇하고 속은 촉촉하게 구워냅니다.',
      cooking_time: '15분',
      difficulty: 'easy',
      servings: 2,
      ingredients: ['식빵(4개)', '크림(120g)', '설탕(30g)', '식용유(20ml)', '계란(2알)'],
      steps: [
        '크림, 설탕, 계란을 볼에 넣고 잘 섞어 반죽물을 만듭니다.',
        '식빵을 반죽물에 충분히 적셔줍니다.',
        '팬에 식용유를 두르고 약불로 달굽니다.',
        '식빵을 올려 양면을 노릇하게 굽습니다.',
        '접시에 담고 기호에 따라 슈거파우더를 뿌립니다.',
      ],
      missing_ingredients: ['계란(2알)'],
    },
    {
      id: 'onion',
      dish_name: '양파 채소볶음',
      emoji: '🧅',
      hero: heroTone.green,
      kind: 'library',
      saved_at: '5월 28일',
      completed_at: '2026-05-29',
      introduction: '양파와 오이를 가볍게 볶아낸 담백한 채소 반찬입니다. 짜지 않게 간을 맞춰 다이어트에도 잘 어울립니다.',
      cooking_time: '12분',
      difficulty: 'easy',
      servings: 2,
      ingredients: ['양파(2개)', '오이(1개)', '식용유(15ml)', '간장(1작은술)'],
      steps: [
        '양파와 오이를 먹기 좋은 크기로 썹니다.',
        '팬에 식용유를 두르고 중불로 달굽니다.',
        '양파를 먼저 넣어 투명해질 때까지 볶습니다.',
        '오이를 넣고 살짝 더 볶습니다.',
        '간장으로 가볍게 간을 맞춰 마무리합니다.',
      ],
      missing_ingredients: [],
    },
    {
      id: 'cucumber',
      dish_name: '오이 무침',
      emoji: '🥒',
      hero: heroTone.green,
      kind: 'library',
      saved_at: '5월 26일',
      completed_at: '2026-05-27',
      introduction: '아삭한 오이에 매콤한 청양고추를 더한 상큼한 밑반찬입니다. 입맛 없을 때 곁들이기 좋습니다.',
      cooking_time: '10분',
      difficulty: 'easy',
      servings: 2,
      ingredients: ['오이(2개)', '청양고추(2개)', '설탕(1작은술)', '간장(1작은술)'],
      steps: [
        '오이를 어슷하게 썰어 소금에 살짝 절입니다.',
        '청양고추를 잘게 썹니다.',
        '물기를 짠 오이에 청양고추, 설탕, 간장을 넣습니다.',
        '골고루 무쳐 그릇에 담아냅니다.',
      ],
      missing_ingredients: [],
    },
  ];

  // ---- 칸놀리 데모 플로우 (채팅 시뮬레이션용) ----
  const demo = {
    vision: {
      dish_name: '칸놀리',
      ingredients: ['밀가루', '크림', '설탕', '건포도'],
      characteristics:
        '겉면은 진한 황금빛으로 바삭하게 튀겨졌고, 속에는 부드러운 흰 크림이 채워져 있습니다. 윗면에 슈거파우더가 뿌려진 전형적인 이탈리아 칸놀리의 플레이팅입니다.',
    },
    recipe: recipes[0],
    // 확정 시 미구매 재료 쇼핑 결과 (네이버)
    shopping: {},
  };

  // 프렌치토스트 미구매(계란) 쇼핑 데모
  const shoppingEgg = [
    { title: '동물복지 유정란 특란 30구 신선 계란', price: 12900, mall: 'NAVER', tone: '#F6EFD9' },
    { title: '무항생제 대란 20구 아침 신선란', price: 8500, mall: 'NAVER', tone: '#F1ECDE' },
    { title: '풀무원 목초란 자연방사 계란 10구', price: 6900, mall: 'NAVER', tone: '#EFE9DA' },
  ];

  window.DATA = { kitchen, recipes, demo, heroTone, shoppingEgg };
})();

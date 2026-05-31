/* ============================================================
   레시피 AI — Home board (이전 채팅/레시피 메인보드)
   ============================================================ */
(function () {
  const { Icon } = window;

  function HomeBoard({ recipes, kitchen, layout = 'grid', onNewChat, onOpenRecipe, setView }) {
    const cart = recipes.filter((r) => r.kind === 'cart');
    const done = recipes.filter((r) => r.kind === 'library');

    const stats = [
      { ic: React.createElement(Icon.bookmark, { size: 18 }), v: recipes.length, k: '저장된 레시피', tone: 'var(--blue)', bg: 'var(--blue-soft)' },
      { ic: React.createElement(Icon.cart, { size: 18 }), v: cart.length, k: '장바구니 대기', tone: 'var(--amber-ink)', bg: 'var(--amber-soft)' },
      { ic: React.createElement(Icon.checkCircle, { size: 18 }), v: done.length, k: '완료한 요리', tone: 'var(--green-ink)', bg: 'var(--green-soft)' },
      { ic: React.createElement(Icon.fridge, { size: 18 }), v: kitchen.ingredients.length, k: '보유 재료', tone: 'var(--ink-2)', bg: 'var(--surface-3)' },
    ];

    return React.createElement('div', { className: 'scroll' },
      React.createElement('div', { className: 'board' },
        // hero
        React.createElement('div', { className: 'board-hero fade-up' },
          React.createElement('div', { className: 'bh-eyebrow' }, '오늘은 어떤 요리를 해볼까요?'),
          React.createElement('div', { className: 'bh-title' }, '냉장고 속 음식 사진,\n레시피로 바꿔드릴게요'),
          React.createElement('div', { className: 'bh-sub' },
            '음식 사진을 올리면 AI가 재료를 분석하고, 내 주방에 있는 재료에 맞춰 딱 맞는 한국어 레시피를 만들어 드려요.'),
          React.createElement('div', { className: 'bh-cta' },
            React.createElement('button', { className: 'bh-btn', onClick: onNewChat },
              React.createElement(Icon.camera, { size: 18 }), '음식 사진으로 시작하기'),
            React.createElement('button', { className: 'bh-btn ghost', onClick: () => setView('kitchen') },
              React.createElement(Icon.fridge, { size: 18 }), '내 주방 관리')
          )
        ),

        // stats
        React.createElement('div', { className: 'stat-row' },
          stats.map((s, i) =>
            React.createElement('div', { className: 'stat-card fade-up', key: i, style: { animationDelay: (i * 0.04 + 0.05) + 's' } },
              React.createElement('div', { className: 'stat-ic', style: { background: s.bg, color: s.tone } }, s.ic),
              React.createElement('div', { className: 'stat-v' }, s.v),
              React.createElement('div', { className: 'stat-k' }, s.k)
            )
          )
        ),

        // 장바구니 (이어서 완료할 레시피)
        cart.length > 0 ? React.createElement(React.Fragment, null,
          React.createElement('div', { className: 'board-row' },
            React.createElement('h2', null, '🛒 이어서 완료하기'),
            React.createElement('button', { className: 'link', onClick: () => setView('kitchen') },
              '주방 재료 보기', React.createElement(Icon.chevR, { size: 15 }))
          ),
          layout === 'grid'
            ? React.createElement('div', { className: 'recipe-grid' }, cart.map((r) => tile(r, onOpenRecipe)))
            : React.createElement('div', { className: 'recipe-list' }, cart.map((r) => listRow(r, onOpenRecipe)))
        ) : null,

        // 최근 레시피 (모든 채팅 기록)
        React.createElement('div', { className: 'board-row' },
          React.createElement('h2', null, '최근 레시피 기록'),
          React.createElement('span', { style: { fontSize: 12.5, color: 'var(--ink-3)', fontWeight: 600 } },
            recipes.length + '개 · 음식 사진에서 생성됨')
        ),
        layout === 'grid'
          ? React.createElement('div', { className: 'recipe-grid' }, recipes.map((r) => tile(r, onOpenRecipe)))
          : React.createElement('div', { className: 'recipe-list' }, recipes.map((r) => listRow(r, onOpenRecipe)))
      )
    );
  }

  function tile(r, onOpen) {
    const isCart = r.kind === 'cart';
    return React.createElement('button', { key: r.id, className: 'r-tile fade-up', onClick: () => onOpen(r) },
      React.createElement('div', { className: 'r-tile-hero ph', style: { background: r.hero } },
        React.createElement('span', { style: { fontSize: 34, filter: 'saturate(.9)' } }, r.emoji),
        React.createElement('span', { className: 'r-tile-badge ' + (isCart ? 'badge-cart' : 'badge-done') },
          isCart ? React.createElement(Icon.cart, { size: 13 }) : React.createElement(Icon.checkCircle, { size: 13 }),
          isCart ? '장바구니' : '완료')
      ),
      React.createElement('div', { className: 'r-tile-body' },
        React.createElement('div', { className: 'r-tile-name' }, r.dish_name),
        React.createElement('div', { className: 'r-tile-intro' }, r.introduction),
        React.createElement('div', { className: 'r-tile-foot' },
          React.createElement('span', null, React.createElement(Icon.clock, { size: 14 }), r.cooking_time),
          React.createElement('span', null, React.createElement(Icon.users, { size: 14 }), r.servings + '인분'),
          React.createElement('span', { style: { marginLeft: 'auto' } }, r.saved_at)
        )
      )
    );
  }

  function listRow(r, onOpen) {
    const isCart = r.kind === 'cart';
    return React.createElement('button', { key: r.id, className: 'r-listrow fade-up', onClick: () => onOpen(r) },
      React.createElement('div', { className: 'r-listrow-thumb ph', style: { background: r.hero, fontSize: 22 } }, r.emoji),
      React.createElement('div', { style: { minWidth: 0, flex: 1 } },
        React.createElement('div', { className: 'r-listrow-name' }, r.dish_name),
        React.createElement('div', { className: 'r-listrow-intro' }, r.introduction)
      ),
      React.createElement('span', { className: 'tag ' + (isCart ? 'tag-amber' : 'tag-green') },
        isCart ? '장바구니' : '완료'),
      React.createElement('span', { style: { fontSize: 12, color: 'var(--ink-3)', fontWeight: 600, minWidth: 64, textAlign: 'right' } },
        r.cooking_time),
      React.createElement(Icon.chevR, { size: 17, style: { color: 'var(--ink-4)' } })
    );
  }

  window.HomeBoard = HomeBoard;
})();

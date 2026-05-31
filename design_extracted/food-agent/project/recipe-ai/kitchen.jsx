/* ============================================================
   레시피 AI — Kitchen view (내 주방: 재료 / 취향 / 완료 처리)
   ============================================================ */
(function () {
  const { Icon } = window;
  const { useState } = React;

  const PREF_ICON = {
    allergy: { ic: Icon.ban, bg: 'var(--rose-soft)', color: 'var(--rose)' },
    avoid: { ic: Icon.ban, bg: 'var(--amber-soft)', color: 'var(--amber-ink)' },
    like: { ic: Icon.heart, bg: 'var(--green-soft)', color: 'var(--green-ink)' },
    diet: { ic: Icon.leaf, bg: 'var(--blue-soft)', color: 'var(--blue-ink)' },
  };

  function KitchenView({ kitchen, setKitchen, recipes, onComplete }) {
    const [newIng, setNewIng] = useState('');
    const cart = recipes.filter((r) => r.kind === 'cart');

    function addIng() {
      const t = newIng.trim();
      if (!t) return;
      const m = t.match(/^(.+?)\((.*)\)$/);
      const item = m ? { name: m[1].trim(), amount: m[2].trim() } : { name: t, amount: '' };
      setKitchen({ ...kitchen, ingredients: [...kitchen.ingredients, item] });
      setNewIng('');
    }
    function removeIng(idx) {
      setKitchen({ ...kitchen, ingredients: kitchen.ingredients.filter((_, i) => i !== idx) });
    }
    function removePref(idx) {
      setKitchen({ ...kitchen, preferences: kitchen.preferences.filter((_, i) => i !== idx) });
    }

    return React.createElement('div', { className: 'main' },
      React.createElement('div', { className: 'topbar' },
        React.createElement('div', { className: 'k-panel-ic', style: { width: 34, height: 34, background: 'var(--blue-soft)', color: 'var(--blue)' } },
          React.createElement(Icon.fridge, { size: 18 })),
        React.createElement('div', null,
          React.createElement('div', { className: 'topbar-title' }, '내 주방'),
          React.createElement('div', { className: 'topbar-sub' }, '보유 재료와 취향을 관리하면 레시피가 더 정확해져요')),
        React.createElement('div', { className: 'topbar-spacer' }),
        React.createElement('div', { style: { fontSize: 12.5, color: 'var(--ink-3)', fontWeight: 600 } },
          '최종 갱신 ', React.createElement('span', { className: 'mono' }, kitchen.updated))
      ),
      React.createElement('div', { className: 'scroll' },
        React.createElement('div', { className: 'kitchen' },

          // 완료 처리 대기 (cart)
          cart.length > 0 ? React.createElement('div', { className: 'k-panel fade-up' },
            React.createElement('div', { className: 'k-panel-head' },
              React.createElement('div', { className: 'k-panel-ic', style: { background: 'var(--amber-soft)', color: 'var(--amber-ink)' } },
                React.createElement(Icon.cart, { size: 19 })),
              React.createElement('div', { style: { flex: 1 } },
                React.createElement('div', { className: 'k-panel-title' }, '완료 처리 대기'),
                React.createElement('div', { className: 'k-panel-sub' }, '요리를 마친 레시피를 완료하면 사용한 재료가 자동 차감돼요')),
              React.createElement('span', { className: 'tag tag-amber' }, cart.length + '개')),
            React.createElement('div', { className: 'k-panel-body', style: { paddingTop: 14 } },
              React.createElement('div', { className: 'recipe-list' },
                cart.map((r) => React.createElement('div', { key: r.id, className: 'r-listrow', style: { cursor: 'default' } },
                  React.createElement('div', { className: 'r-listrow-thumb ph', style: { background: r.hero, fontSize: 22 } }, r.emoji),
                  React.createElement('div', { style: { minWidth: 0, flex: 1 } },
                    React.createElement('div', { className: 'r-listrow-name' }, r.dish_name),
                    React.createElement('div', { className: 'r-listrow-intro' }, '재료 ' + r.ingredients.length + '개 · ' + r.cooking_time)),
                  React.createElement('button', { className: 'btn btn-green btn-sm', onClick: () => onComplete(r) },
                    React.createElement(Icon.check, { size: 15 }), '완료 처리')))))
          ) : null,

          // 재료
          React.createElement('div', { className: 'k-panel fade-up' },
            React.createElement('div', { className: 'k-panel-head' },
              React.createElement('div', { className: 'k-panel-ic', style: { background: 'var(--green-soft)', color: 'var(--green-ink)' } },
                React.createElement(Icon.leaf, { size: 19 })),
              React.createElement('div', { style: { flex: 1 } },
                React.createElement('div', { className: 'k-panel-title' }, '보유 재료'),
                React.createElement('div', { className: 'k-panel-sub' }, '재료명(양) 형식으로 적어주세요 · 양은 g, ml로 통일')),
              React.createElement('span', { className: 'tag tag-green' }, kitchen.ingredients.length + '개')),
            React.createElement('div', { className: 'k-panel-body' },
              React.createElement('div', { className: 'ing-chips' },
                kitchen.ingredients.map((ing, i) => React.createElement('div', { className: 'k-ing', key: i },
                  React.createElement('span', null, ing.name),
                  ing.amount ? React.createElement('span', { className: 'amt' }, ing.amount) : null,
                  React.createElement('button', { className: 'x', onClick: () => removeIng(i) },
                    React.createElement(Icon.x, { size: 13 })))),
              ),
              React.createElement('div', { style: { display: 'flex', gap: 9, marginTop: 16, maxWidth: 360 } },
                React.createElement('div', { className: 'composer-box', style: { flex: 1, padding: '2px 4px 2px 14px' } },
                  React.createElement('input', { className: 'composer-input', style: { fontSize: 13.5, padding: '8px 0' },
                    placeholder: '예: 당근(2개)', value: newIng,
                    onChange: (e) => setNewIng(e.target.value),
                    onKeyDown: (e) => { if (e.key === 'Enter') addIng(); } })),
                React.createElement('button', { className: 'btn btn-soft btn-sm', onClick: addIng },
                  React.createElement(Icon.plus, { size: 16 }), '추가'))
            )),

          // 사용자 취향
          React.createElement('div', { className: 'k-panel fade-up' },
            React.createElement('div', { className: 'k-panel-head' },
              React.createElement('div', { className: 'k-panel-ic', style: { background: 'var(--blue-soft)', color: 'var(--blue-ink)' } },
                React.createElement(Icon.heart, { size: 19 })),
              React.createElement('div', { style: { flex: 1 } },
                React.createElement('div', { className: 'k-panel-title' }, '사용자 취향'),
                React.createElement('div', { className: 'k-panel-sub' }, '알러지·식단·선호 맛 — 모든 레시피에 자동 반영돼요')),
              React.createElement('span', { className: 'tag tag-blue' }, kitchen.preferences.length + '개')),
            React.createElement('div', { className: 'k-panel-body' },
              React.createElement('div', { className: 'pref-list' },
                kitchen.preferences.map((p, i) => {
                  const cfg = PREF_ICON[p.kind] || PREF_ICON.like;
                  return React.createElement('div', { className: 'pref-row', key: i },
                    React.createElement('span', { className: 'pref-ic', style: { background: cfg.bg, color: cfg.color } },
                      React.createElement(cfg.ic, { size: 14 })),
                    React.createElement('span', { className: 'pref-tx' }, p.tx),
                    React.createElement('span', { className: 'tag ' + tagFor(p.kind) }, labelFor(p.kind)),
                    React.createElement('button', { className: 'x', onClick: () => removePref(i) },
                      React.createElement(Icon.x, { size: 15 })));
                }),
                React.createElement('button', { className: 'k-add', style: { marginTop: 4, alignSelf: 'flex-start' },
                  onClick: () => setKitchen({ ...kitchen, preferences: [...kitchen.preferences, { tx: '새 취향을 입력하세요', kind: 'like' }] }) },
                  React.createElement(Icon.plus, { size: 15 }), '취향 추가'))
            ))
        )
      )
    );
  }

  function tagFor(k) { return k === 'allergy' ? 'tag-amber' : k === 'avoid' ? 'tag-amber' : k === 'diet' ? 'tag-blue' : 'tag-green'; }
  function labelFor(k) { return { allergy: '알러지', avoid: '기피', like: '선호', diet: '식단' }[k] || '선호'; }

  window.KitchenView = KitchenView;
})();

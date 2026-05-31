/* ============================================================
   레시피 AI — Shared components (Sidebar, RecipeCard, helpers)
   ============================================================ */
(function () {
  const { Icon } = window;
  const DIFF = { easy: '쉬움', medium: '보통', hard: '어려움' };
  const DIFF_TONE = { easy: 'tag-green', medium: 'tag-blue', hard: 'tag-amber' };

  // 재료 문자열 "이름(양)" → {name, amount}
  function parseIng(s) {
    const m = String(s).match(/^(.+?)\((.*)\)$/);
    return m ? { name: m[1].trim(), amount: m[2].trim() } : { name: String(s).trim(), amount: '' };
  }

  // ─────────────────────────── SIDEBAR ───────────────────────────
  function Sidebar({ view, setView, recipes, onNewChat, onOpenRecipe, activeRecipeId }) {
    const cart = recipes.filter((r) => r.kind === 'cart');
    const library = recipes.filter((r) => r.kind === 'library');
    const navItem = (id, icon, label, count) =>
      React.createElement(
        'button',
        { className: 'sb-nav-item' + (view === id ? ' active' : ''), onClick: () => setView(id) },
        icon, React.createElement('span', null, label),
        count != null ? React.createElement('span', { className: 'sb-nav-count' }, count) : null
      );

    return React.createElement(
      'aside', { className: 'sidebar' },
      React.createElement(
        'div', { className: 'sb-brand' },
        React.createElement('div', { className: 'sb-logo' }, React.createElement(Icon.chef, { size: 21 })),
        React.createElement('div', null,
          React.createElement('div', { className: 'sb-brand-name' }, '레시피 AI'),
          React.createElement('div', { className: 'sb-brand-sub' }, '사진 한 장으로 요리 시작')
        )
      ),
      React.createElement('button', { className: 'sb-new', onClick: onNewChat },
        React.createElement(Icon.camera, { size: 17 }), '새 레시피 만들기'),
      React.createElement('nav', { className: 'sb-nav' },
        navItem('home', React.createElement(Icon.home, { size: 18 }), '홈'),
        navItem('chat', React.createElement(Icon.chat, { size: 18 }), '레시피 채팅'),
        navItem('kitchen', React.createElement(Icon.fridge, { size: 18 }), '내 주방'),
      ),
      React.createElement('div', { className: 'sb-section-label' }, '저장된 레시피'),
      React.createElement('div', { className: 'sb-saved' },
        cart.length === 0 && library.length === 0
          ? React.createElement('div', { style: { fontSize: 12.5, color: 'var(--ink-3)', padding: '6px 10px' } }, '아직 저장된 레시피가 없어요.')
          : null,
        cart.map((r) => recipeRow(r, '🛒', 'dot-cart', activeRecipeId, onOpenRecipe, '장바구니 · ' + r.saved_at)),
        library.map((r) => recipeRow(r, '✅', 'dot-done', activeRecipeId, onOpenRecipe, '보관함 · 완료')),
      ),
      React.createElement('div', { className: 'sb-foot' },
        React.createElement('div', { className: 'sb-avatar' }, 'JK'),
        React.createElement('div', { style: { lineHeight: 1.3 } },
          React.createElement('div', { style: { fontSize: 13, fontWeight: 700 } }, '준규님의 주방'),
          React.createElement('div', { style: { fontSize: 11, color: 'var(--ink-3)' } }, 'Groq · Llama 4 Scout')
        )
      )
    );
  }

  function recipeRow(r, emoji, dotClass, activeId, onOpen, meta) {
    return React.createElement(
      'button',
      { key: r.id, className: 'sb-recipe' + (activeId === r.id ? ' active' : ''), onClick: () => onOpen(r) },
      React.createElement('div', { className: 'sb-recipe-thumb' }, r.emoji || emoji),
      React.createElement('div', { style: { minWidth: 0, flex: 1 } },
        React.createElement('div', { className: 'sb-recipe-name' }, r.dish_name),
        React.createElement('div', { className: 'sb-recipe-meta' }, meta)
      ),
      React.createElement('span', { className: 'sb-status-dot ' + dotClass })
    );
  }

  // ─────────────────────────── RECIPE CARD ───────────────────────────
  // variant: 'classic' | 'magazine' | 'compact'
  function RecipeCard({ recipe, variant = 'classic', kitchen, showHero = false }) {
    const have = new Set((kitchen?.ingredients || []).map((i) => i.name));
    const missing = new Set((recipe.missing_ingredients || []).map((m) => parseIng(m).name));
    const ings = (recipe.ingredients || []).map(parseIng);

    const meta = React.createElement('div', { className: 'rc-meta' },
      metaItem(React.createElement(Icon.clock, { size: 16 }), '조리 시간', recipe.cooking_time || '-'),
      metaItem(React.createElement(Icon.gauge, { size: 16 }), '난이도', DIFF[recipe.difficulty] || '-'),
      metaItem(React.createElement(Icon.users, { size: 16 }), '인분', (recipe.servings ? recipe.servings + '인분' : '-')),
    );

    const ingSection = React.createElement('div', { className: 'rc-section' },
      React.createElement('div', { className: 'rc-section-title' },
        React.createElement(Icon.leaf, { size: 17, style: { color: 'var(--green)' } }),
        '재료',
        React.createElement('span', { className: 'n' }, ings.length + '개')
      ),
      React.createElement('div', { className: 'ing-grid' },
        ings.map((ing, i) => {
          const isMissing = missing.has(ing.name);
          const isHave = !isMissing && have.has(ing.name);
          return React.createElement('div',
            { key: i, className: 'ing-pill' + (isHave ? ' have' : '') + (isMissing ? ' missing' : '') },
            React.createElement('span', { className: 'ing-check' }, React.createElement(Icon.check, { size: 12, sw: 2.4 })),
            React.createElement('span', { className: 'ing-name' }, ing.name),
            React.createElement('span', { className: 'ing-amt mono' }, isMissing ? '구매 필요' : (ing.amount || '')),
          );
        })
      )
    );

    const stepSection = React.createElement('div', { className: 'rc-section' },
      React.createElement('div', { className: 'rc-section-title' },
        React.createElement(Icon.chef, { size: 17, style: { color: 'var(--blue)' } }),
        '조리법',
        React.createElement('span', { className: 'n' }, (recipe.steps || []).length + '단계')
      ),
      (recipe.steps || []).map((s, i) =>
        React.createElement('div', { className: 'step', key: i },
          React.createElement('div', { className: 'step-n' }, i + 1),
          React.createElement('div', { className: 'step-tx' }, s)
        )
      )
    );

    const head = React.createElement('div', { className: 'rc-head' },
      React.createElement('div', { className: 'rc-eyebrow' }, '맞춤 레시피'),
      React.createElement('div', { className: 'rc-title' }, recipe.dish_name),
      recipe.introduction ? React.createElement('div', { className: 'rc-intro' }, recipe.introduction) : null
    );

    const hero = (showHero || variant === 'magazine')
      ? React.createElement('div', { className: 'rc-hero ph food', style: { height: 150, background: recipe.hero } },
          React.createElement('span', null, '음식 사진'))
      : null;

    return React.createElement('div', { className: 'recipe-card ' + variant },
      hero, head, meta, ingSection, stepSection
    );
  }

  function metaItem(ic, k, v) {
    return React.createElement('div', { className: 'rc-meta-item' },
      React.createElement('span', { className: 'rc-meta-ic' }, ic),
      React.createElement('div', null,
        React.createElement('div', { className: 'rc-meta-k' }, k),
        React.createElement('div', { className: 'rc-meta-v mono' }, v)
      )
    );
  }

  // ─────────────────────────── TYPING BUBBLE ───────────────────────────
  function TypingBubble() {
    return React.createElement('div', { className: 'msg-ai fade-up' },
      React.createElement('div', { className: 'msg-ai-avatar' }, React.createElement(Icon.chef, { size: 18 })),
      React.createElement('div', { className: 'bubble-ai' },
        React.createElement('div', { className: 'typing' },
          React.createElement('i'), React.createElement('i'), React.createElement('i'))
      )
    );
  }

  Object.assign(window, { Sidebar, RecipeCard, TypingBubble, parseIng, DIFF, DIFF_TONE });
})();

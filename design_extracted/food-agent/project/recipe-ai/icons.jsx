/* ============================================================
   레시피 AI — Icons (stroke-based, 1.75 weight)
   window.Icon.{name}
   ============================================================ */
(function () {
  const S = (paths, props = {}) => (p = {}) => {
    const size = p.size || 20;
    return React.createElement(
      'svg',
      {
        width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
        stroke: 'currentColor', strokeWidth: p.sw || 1.75,
        strokeLinecap: 'round', strokeLinejoin: 'round',
        style: p.style, ...props,
      },
      paths.map((d, i) =>
        typeof d === 'string'
          ? React.createElement('path', { key: i, d })
          : React.createElement(d.tag, { key: i, ...d.attr })
      )
    );
  };

  const Icon = {
    spark: S(['M12 3v3M12 18v3M3 12h3M18 12h3', 'M12 8.5a3.5 3.5 0 0 0 3.5 3.5A3.5 3.5 0 0 0 12 15.5 3.5 3.5 0 0 0 8.5 12 3.5 3.5 0 0 0 12 8.5Z']),
    chef: S([
      'M6 14h12v5a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-5Z',
      'M7 14a4 4 0 0 1-1-7.9A3.5 3.5 0 0 1 12 4a3.5 3.5 0 0 1 6 2.1A4 4 0 0 1 17 14',
      'M9 17h.01M12 17h.01M15 17h.01',
    ]),
    home: S(['M3 10.5 12 4l9 6.5', 'M5 9.5V20h14V9.5', { tag: 'path', attr: { d: 'M9.5 20v-5h5v5' } }]),
    chat: S(['M4 5h16v11H8l-4 4V5Z', 'M8.5 10h7M8.5 13h4']),
    fridge: S(['M6 3h12v18H6zM6 9h12M9.5 5.5v1.5M9.5 12v3']),
    bookmark: S(['M6 4h12v16l-6-4-6 4V4Z']),
    cart: S(['M4 5h2l1.6 9.3a1 1 0 0 0 1 .7h7.8a1 1 0 0 0 1-.8L20 8H7', { tag: 'circle', attr: { cx: 9, cy: 19, r: 1.4 } }, { tag: 'circle', attr: { cx: 17, cy: 19, r: 1.4 } }]),
    camera: S(['M4 8h3l1.5-2h7L17 8h3v11H4V8Z', { tag: 'circle', attr: { cx: 12, cy: 13, r: 3.2 } }]),
    image: S(['M4 5h16v14H4zM4 16l4.5-4.5 4 4L16 12l4 4', { tag: 'circle', attr: { cx: 9, cy: 9, r: 1.4 } }]),
    upload: S(['M12 16V5M8 9l4-4 4 4', 'M5 19h14']),
    send: S(['M5 12 20 5l-4 15-4-6-7-2Z']),
    plus: S(['M12 5v14M5 12h14']),
    check: S(['M5 12.5 10 17l9-10']),
    checkCircle: S([{ tag: 'circle', attr: { cx: 12, cy: 12, r: 9 } }, 'M8.5 12.5 11 15l4.5-5.5']),
    x: S(['M6 6l12 12M18 6 6 18']),
    edit: S(['M5 19h14', 'M14.5 5.5l3 3M6 16l9-9 3 3-9 9H6v-3Z']),
    refresh: S(['M20 11a8 8 0 0 0-14-4.5L4 8M4 4v4h4', 'M4 13a8 8 0 0 0 14 4.5L20 16M20 20v-4h-4']),
    clock: S([{ tag: 'circle', attr: { cx: 12, cy: 12, r: 8.5 } }, 'M12 7.5V12l3 2']),
    gauge: S(['M5 17a8 8 0 1 1 14 0', 'M12 17l3.5-5']),
    users: S([{ tag: 'circle', attr: { cx: 9, cy: 8, r: 3 } }, 'M3.5 19a5.5 5.5 0 0 1 11 0', 'M16 5.3a3 3 0 0 1 0 5.4M16.5 13.2A5.5 5.5 0 0 1 20.5 18.5']),
    leaf: S(['M5 19c0-8 5-13 14-13 0 9-5 14-14 13Z', 'M9 15c2-2.5 4.5-4.5 7-5.5']),
    flame: S(['M12 3c1 3 4 4 4 8a4 4 0 0 1-8 0c0-1 .3-2 1-2.6C9 11 12 9 12 3Z']),
    ban: S([{ tag: 'circle', attr: { cx: 12, cy: 12, r: 8.5 } }, 'M6 6l12 12']),
    heart: S(['M12 20S4 14.5 4 9a4 4 0 0 1 8-1 4 4 0 0 1 8 1c0 5.5-8 11-8 11Z']),
    scale: S(['M12 4v16M7 8h10', 'M7 8l-3 6h6l-3-6ZM17 8l-3 6h6l-3-6Z']),
    sliders: S(['M5 8h9M18 8h1M5 16h1M10 16h9', { tag: 'circle', attr: { cx: 16, cy: 8, r: 2 } }, { tag: 'circle', attr: { cx: 8, cy: 16, r: 2 } }]),
    arrowRight: S(['M5 12h14M13 6l6 6-6 6']),
    chevR: S(['M9 6l6 6-6 6']),
    sparkle2: S(['M12 4l1.6 4.8L18 10l-4.4 1.2L12 16l-1.6-4.8L6 10l4.4-1.2L12 4Z']),
    bag: S(['M6 8h12l-1 12H7L6 8Z', 'M9 8a3 3 0 0 1 6 0']),
    trash: S(['M5 7h14M9 7V5h6v2M7 7l1 13h8l1-13']),
    book: S(['M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V4Z', 'M5 16h13']),
    photo2: S([{ tag: 'rect', attr: { x: 3, y: 5, width: 18, height: 14, rx: 2 } }, 'M3 15l5-4 4 3 3-3 6 5']),
    wand: S(['M5 19l9-9M14 6l1.5-1.5M18 10l1.5-.5M15.5 8.5 17 7', 'M14 10l-1-1']),
  };

  window.Icon = Icon;
})();

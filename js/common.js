export const loadCss = (cssFile) => {
    const cssPath = import.meta.resolve(cssFile);
    //console.log(cssPath);
    const $link = document.createElement("link");
    $link.setAttribute("rel", 'stylesheet');
    $link.setAttribute("href", cssPath);
    document.head.appendChild($link);
};

export const addCss = (css) => {
    const $style = document.createElement("style");
    $style.textContent = css;
    document.head.appendChild($style);
};
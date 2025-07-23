document.addEventListener('DOMContentLoaded', (event)=>{
    const checkbox = document.getElementById('checkbox');
    const body = document.body;

    const savedTheme = localStorage.getItem('theme')

    if (savedTheme === 'dark'){
        body.classList.add('dark-mode');
        checkbox.checked = true;
    }
    else{
        body.classList.remove('dark-mode')
        checkbox.checked = false
    }

    checkbox.addEventListener('change', ()=>{
        if (checkbox.checked){
            body.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark')
        }
        else{
            body.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light')
        }
    })
})
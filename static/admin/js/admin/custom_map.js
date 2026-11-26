// custom_map.js
document.addEventListener("DOMContentLoaded", function () {
    var map = L.map('map').setView([46.4825, 30.7326], 10); // Одесса, Украина по умолчанию

    // Подключаем OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Функция для отображения текущего местоположения пользователя
    function locateUser() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function (position) {
                var userLocation = [position.coords.latitude, position.coords.longitude];
                var userMarker = L.marker(userLocation).addTo(map).bindPopup("Ваше местоположение");
                map.setView(userLocation, 14);  // Перемещаем карту на местоположение пользователя
            }, function (error) {
                console.error("Ошибка геолокации: ", error);
                alert("Не удалось получить местоположение.");
            });
        } else {
            alert("Геолокация не поддерживается вашим браузером.");
        }
    }

    locateUser();  // Запуск геолокации при загрузке страницы
});
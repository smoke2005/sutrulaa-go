function fetchWeather(city) {
    fetch(`/get-weather/${city}`)
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById("weatherData").innerHTML = "Could not fetch weather data.";
        } else {
            document.getElementById("weatherTitle").innerText = `Weather in ${city}`;
            document.getElementById("weatherData").innerHTML = `
                Temperature: ${data.temperature} °C <br>
                Weather: ${data.weather} <br>
                Humidity: ${data.humidity}% <br>
                Cloud Cover: ${data.clouds}% <br>
                Wind Speed: ${data.wind_speed} m/s
            `;
        }
        document.getElementById("weatherModal").style.display = "block";
    })
    .catch(error => {
        console.error("Error fetching weather:", error);
        document.getElementById("weatherData").innerHTML = "Failed to fetch weather info.";
        document.getElementById("weatherModal").style.display = "block";
    });
}

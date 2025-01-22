document.addEventListener("DOMContentLoaded", function () {
  const routeInput = document.getElementById("route-search");
  const routeSelect = document.getElementById("route");

  const allOptions = Array.from(routeSelect.options);

  routeInput.addEventListener("input", function () {
    const filter = routeInput.value.toLowerCase();
    let displayedCount = 0;

    allOptions.forEach((option) => {
      if (option.value.toLowerCase().includes(filter) && displayedCount < 5) {
        option.style.display = "";
        displayedCount++;
      } else {
        option.style.display = "none";
      }
    });
  });
});

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('recommendation-form');
    const resultsSection = document.getElementById('results-section');
    const resultsGrid = document.getElementById('results-grid');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // 1. Gather User Input
        const location = document.getElementById('location').value;
        const maxPrice = document.getElementById('max-price').value;
        const tripDesc = document.getElementById('trip-desc').value;
        const amenitiesNodes = document.querySelectorAll('input[name="amenities"]:checked');
        const amenities = Array.from(amenitiesNodes).map(node => node.value);

        // 2. Prepare Payload
        const payload = {
            location: location || undefined,
            min_price: 0,
            max_price: maxPrice ? parseFloat(maxPrice) : 10000,
            required_amenities: amenities,
            trip_description: tripDesc || undefined
        };

        // 3. Show Loading State (Optional UI polish)
        resultsSection.classList.remove('hidden');
        resultsGrid.innerHTML = `
            <div class="glass-panel" style="text-align:center">
                <div style="font-size:1.2rem; margin-bottom:0.5rem">🤖 AI is thinking...</div>
                <div style="color:#94a3b8">Ranking hotels based on your vibe.</div>
            </div>`;

        try {
            // 4. Call API
            const response = await fetch('/recommendations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Failed to fetch recommendations');

            const recommendations = await response.json();
            renderResults(recommendations);

        } catch (error) {
            console.error('Error:', error);
            resultsGrid.innerHTML = `<div class="glass-panel" style="color:#ef4444;text-align:center">Something went wrong. Please try again.</div>`;
        }
    });

    function renderResults(recommendations) {
        resultsGrid.innerHTML = '';

        if (recommendations.length === 0) {
            resultsGrid.innerHTML = '<div class="glass-panel" style="text-align:center">No hotels found matching your criteria. Try adjusting filters.</div>';
            return;
        }

        recommendations.forEach((item, index) => {
            const hotel = item.hotel;
            const score = Math.round(item.score);
            const isTopPick = index === 0;

            const card = document.createElement('div');
            card.className = `hotel-card ${isTopPick ? 'top-pick' : ''}`;

            card.innerHTML = `
                <div class="card-header">
                    <div>
                        <div class="hotel-name">${hotel.name}</div>
                        <div class="hotel-location">📍 ${hotel.location}</div>
                    </div>
                    <div style="text-align:right">
                        <div class="hotel-price">$${hotel.price}</div>
                        <div class="rating-badge">★ ${hotel.rating}</div>
                    </div>
                </div>

                <div class="amenities-tags">
                    ${hotel.amenities.map(a => `<span class="tag">${a}</span>`).join('')}
                </div>

                <div class="ai-reason">
                    <strong>Why we picked this</strong>
                    ${item.reasoning}
                </div>
                
                <button class="cta-button" style="margin-top:1rem; font-size:0.9rem; padding:0.8rem" onclick="bookHotel(${hotel.id}, '${hotel.name}')">
                    Book Now
                </button>
            `;

            resultsGrid.appendChild(card);
        });
    }

    // Expose to global scope for onclick
    window.bookHotel = async (hotelId, hotelName) => {
        const email = prompt(`Enter your email to book ${hotelName}:`, "user@example.com");
        if (!email) return;

        try {
            const response = await fetch('/bookings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-token': 'secret-token' // Simulating Auth
                },
                body: JSON.stringify({
                    hotel_id: hotelId,
                    user_email: email,
                    guest_name: "Workshop Guest"
                })
            });

            if (response.ok) {
                const data = await response.json();
                alert(`✅ ${data.message}`);
            } else {
                alert("❌ Booking failed! (Did you check the Auth token?)");
            }
        } catch (error) {
            console.error(error);
            alert("Error connecting to server.");
        }
    };
});

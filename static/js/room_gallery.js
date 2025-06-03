let roomImages = {};
let currentRoom = null;
let currentImg = 0;

function openRoomGallery(roomId, imgIndex) {
  currentRoom = roomId;
  currentImg = imgIndex;
  const imgs = roomImages[roomId];
  document.getElementById("room-modal-img").src = imgs[imgIndex];
  document.getElementById("room-modal").style.display = "block";
}

function closeRoomGallery() {
  document.getElementById("room-modal").style.display = "none";
}

function prevRoomImg() {
  const imgs = roomImages[currentRoom];
  currentImg = (currentImg - 1 + imgs.length) % imgs.length;
  document.getElementById("room-modal-img").src = imgs[currentImg];
}

function nextRoomImg() {
  const imgs = roomImages[currentRoom];
  currentImg = (currentImg + 1) % imgs.length;
  document.getElementById("room-modal-img").src = imgs[currentImg];
}

// https://www-hj.douyin.com/aweme/v1/web/mix/aweme/?mix_id=7379202439423772710&cursor=47&count=1
// https://www-hj.douyin.com/aweme/v1/web/aweme/detail/?aweme_id=[video_id]
// $$("#user_detail_element ul a").map(e => e.href) [video/video_id]

// https://www.douyin.com/user/...
let userPostData=((e=["web/aweme/post"])=>{const t=[],s=XMLHttpRequest.prototype.open;return XMLHttpRequest.prototype.open=function(r,o,...p){return this._url=o,this.addEventListener("load",function(){if(this._url&&e.some(e=>this._url.includes(e)))try{t.push(JSON.parse(this.responseText))}catch(e){console.error("Failed to parse response:",e)}}),s.apply(this,[r,o,...p])},t})();
let seriesPostData=((e=["web/series/aweme"])=>{const t=[],s=XMLHttpRequest.prototype.open;return XMLHttpRequest.prototype.open=function(r,o,...p){return this._url=o,this.addEventListener("load",function(){if(this._url&&e.some(e=>this._url.includes(e)))try{t.push(JSON.parse(this.responseText))}catch(e){console.error("Failed to parse response:",e)}}),s.apply(this,[r,o,...p])},t})();
let set_data=(t,e,n="vi_VN")=>{if(!e)return t;for(let r=0;r<t.length;r++)e[r]&&(t[r][n]=e[r]);return t};
let download_data=(t,e="data.json")=>{if(!t)return;const n="data:text/json;charset=utf-8,"+encodeURIComponent(JSON.stringify(t,null,2)),o=document.createElement("a");o.setAttribute("href",n),o.setAttribute("download",e),document.body.appendChild(o),o.click(),o.remove()};
let download_txt = function(e,t="douyin_titles.txt"){const o=Array.isArray(e)?e.join("\n"):e,n=new Blob([o],{type:"text/plain;charset=utf-8"}),d=URL.createObjectURL(n),c=document.createElement("a");c.href=d,c.download=t,document.body.appendChild(c),c.click(),document.body.removeChild(c),URL.revokeObjectURL(d)}
let exportIdmNamedQueue=function(e,file_name="idm_queue.txt"){if(!Array.isArray(e)||0===e.length)return;let t="";e.forEach(e=>{e&&e.url&&(t+=e.url+"\r\n")});const r=new Blob([t],{type:"text/plain;charset=utf-8"}),n=document.createElement("a");n.href=URL.createObjectURL(r),n.download=file_name,n.click(),URL.revokeObjectURL(n.href)};
let extractDouyinVideos=function(t){const e=[];return t&&t.aweme_list?(t.aweme_list.forEach(t=>{const i=t.aweme_id||"",a=t.item_title||t.desc||t.caption||'';let r,l,d,_=null,c=t.duration;if(t.video&&Array.isArray(t.video.bit_rate)){let e=-1,i=null;t.video.bit_rate.forEach(t=>{if(t&&t.play_addr){const a=t.play_addr.data_size||0;a>e&&(e=a,i=t.play_addr),r=i.data_size,l=i.width,d=i.height}}),i&&Array.isArray(i.url_list)&&i.url_list.length>0&&(_=i.url_list[0])}let s=t.statistics;e.push({create_time:t.create_time,item_title:a,aweme_id:i,url:_,mime:{duration:c,data_size:r,width:l,height:d},stat:{admire:s.admire_count,collect:s.collect_count,cmt:s.comment_count,digg:s.digg_count,share:s.share_count}})}),e):e};
let arrdata=function(jdata=Array){let t=[];for(d of jdata){let r=extractDouyinVideos(d);r&&t.push(...r)}return t};
let down_step=(n=[],t=100,c="TIẾNG VIỆT")=>{const g=prompt("Tối đa số từ cho mỗi dòng: ")||15;for(let h=0;h<n.length;h+=t){const i=n.slice(h,h+t),e=h/t+1;let l=i.map(n=>n.item_title.replaceAll("\n","").replace(/\s+/g," ").trim()).join("\n"),o=`BẠN LÀ MỘT CHUYÊN GIA DỊCH THUẬT VÀ SÁNG TẠO NỘI DUNG. HÃY THỰC HIỆN YÊU CẦU SAU:\n\nYÊU CẦU CHI TIẾT:\n1. DỊCH SANG ${c.toUpperCase()}: Dịch nội dung được cung cấp sang ${c.toLocaleUpperCase()} tự nhiên, có chút hài hước và tạo sự tò mò cho người đọc.\n2. CẤU TRÚC: Giữ nguyên số lượng dòng (tổng cộng `+i.length+" dòng). Dòng nào tương ứng với dòng đó.\n3. GIỚI HẠN: Mỗi dòng không được vượt quá "+g+" từ, loại bỏ tất cả hastags\n4. CẤM LẶP LẠI: Tuyệt đối không lặp lại các câu mở đầu hoặc các cụm từ gây nhàm chán.\n5. ĐỊNH DẠNG: Chỉ trả về nội dung đã dịch ở định dạng văn bản thuần túy (Plaintext). KHÔNG giải thích, KHÔNG thêm lời chào, KHÔNG bao gồm bất kỳ ký tự thừa nào.\n\nDỮ LIỆU CẦN DỊCH:\n"+l;download_txt(o,`cn_ZH_part${e}_len${i.length}_prompt.txt`)}};

let data_json = arrdata(userPostData||seriesPostData)
// .sort((e,j) => j.stat.digg-e.stat.digg) // desc by actions
// data_json = data_json.sort((a, b) => a.create_time-b.create_time); // desc by uploaded
// data_json = data_json.sort((e,j) => j.mime.data_size-e.mime.data_size) // desc by size

// item_title unique
data_json=Object.values(data_json.reduce((t,e)=>((!t[e.item_title]||e.stat.digg>t[e.item_title].stat.digg)&&(t[e.item_title]=e),t),{}));
// clean url
data_json.forEach(e => e.url = (url => {let x = new URL(url); x.search='';return x.toString()})(e.url))
// Filter
data_json = data_json.sort((e,j) => j.stat.digg-e.stat.digg).filter(e => {let d = e.mime.duration, m = d/(1e3*60); return 1 < m && m < 5})
// calculate GB
Math.sumPrecise(data_json.map(e => e.mime.data_size).filter(e=>e))/Math.pow(1024,3)

// GỬI CÁI NÀY CHO GEMINI DỊCH (translate)
down_step(data_json, 100, 'TIẾNG ANH')
// idm queue
exportIdmNamedQueue(data_json, 'idm_queue.txt')
exportIdmNamedQueue(data_json.filter(e => {let d = e.mime.duration, m = d/(1e3*60); return 8 < m && m < 15}), "idm_queue_8-15.txt")
exportIdmNamedQueue(data_json.filter(e => {let d = e.mime.duration, m = d/(1e3*60); return m > 3}), "idm_queue_3.txt")

// S2: https://gemini.google.com/app
set_data(data_json, prompt('VN translated')?.split('\n').map(e => e.trim().replace('\r', '')), 'vi_VN')
set_data(data_json, prompt('US translated')?.split('\n').map(e => e.trim().replace('\r', '')), 'en_US')
// clean text
data_json.forEach(a=>{["vi_VN","en_US"].forEach(c=>{a[c]&&(a[c]=a[c].replace(/[.,!?]/g,""))})});
download_data(data_json,`data_${data_json.length}.json`)

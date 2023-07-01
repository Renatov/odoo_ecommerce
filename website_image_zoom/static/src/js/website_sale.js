odoo.define('website_image_zoom.website_sale', function (require) {

    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');
    var x = 1;
	publicWidget.registry.WebsiteSale.include({
		_updateProductImage: function ($productContainer, displayImage, productId, productTemplateId, newCarousel, isCombinationPossible) {
			this._super($productContainer, displayImage, productId, productTemplateId, newCarousel, isCombinationPossible)
			var $carousel = $productContainer.find('#o-carousel-product');
			var $images_carrusel =  $carousel.find('.ex1').find('img.img-fluid.product_detail_img')
			$($images_carrusel).simpleLightbox({ sourceAttr: 'src', fileExt: 'png|jpg|jpeg|gif|webp|image_1024|image_256',});
		}
	})
});

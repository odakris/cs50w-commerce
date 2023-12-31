from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

# from django.db.models import OuterRef, Subquery

from .models import User, Category, Auction, ImagesUpload, Bid, Wishlist
from .forms import SellForm, BidForm, CommentForm
from .utils import getFirstImage, isUserAuction


def index(request):
    print(f"User: {request.user}")
    return render(request, "auctions/index.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("auctions:index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("auctions:index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("auctions:index"))
    else:
        return render(request, "auctions/register.html")


def categories(request):
    # Get first image for each auction
    images = getFirstImage(ImagesUpload.objects.all())
    
    return render(request, "auctions/categories.html", {
        "all": "All",
        "category": "ALL",
        "categories": Category.objects.all(),
        "auctions": Auction.objects.filter(active=True),
        "images": images
    })


def filter(request, filter):
    # Get first image for each auction
    images = getFirstImage(ImagesUpload.objects.all())

    if filter == "all":
        return categories(request)
    
    return render(request, "auctions/categories.html", {
        "all": "All",
        "category": filter,
        "categories": Category.objects.all(),
        "auctions": Auction.objects.filter(active=True).filter(category=Category.objects.get(name=filter)),
        "images": images
    })
    
# def categories(request):
#     auctions_with_images = Auction.objects.annotate(
#         first_image=Subquery(
#             ImagesUpload.objects.filter(auction=OuterRef('pk')).values('upload')[:1]
#         )
#     )

#     for auction in auctions_with_images:
#         print(auction.first_image)

#     return render(request, "auctions/categories.html", {
#         "title": "All",
#         "categories": Category.objects.all(),
#         "auctions": auctions_with_images,
#         "MEDIA_URL": MEDIA_URL
#     })


def sell(request):
    sell_form = SellForm()

    # POST REQUESTS 
    if request.method == "POST":
        # get informations form form
        sell_form = SellForm(request.POST)
        if sell_form.is_valid():
            title = sell_form.cleaned_data["title"]
            category = sell_form.cleaned_data["category"]
            description = sell_form.cleaned_data["description"]
            starting_bid = sell_form.cleaned_data["starting_bid"]

            # Create auction into model
            new_auction = Auction(
                seller = request.user,
                title = title,
                category = Category.objects.get(pk = category),
                description = description,
                bid = starting_bid
            )
            new_auction.save()

            # Save imported images into model
            for image in request.FILES.getlist("img-upload"):
                new_img = ImagesUpload(
                    seller = request.user,
                    auction = new_auction,
                    upload = image
                )
                new_img.save()

            # Redirect to index
            return HttpResponseRedirect(reverse("auctions:index"))

    # GET REQUESTS
    return render(request, "auctions/sell.html", {
        "sell_form": sell_form,
    })


def auction(request, auction_id):
    bid_form = BidForm()
    current_auction = Auction.objects.get(pk=auction_id)
    images = ImagesUpload.objects.filter(auction=current_auction)
    comment_form = CommentForm()
    isWishlisted = ""
    # Defined if current auction is user's or not
    closeButton = isUserAuction(request.user, current_auction.pk)

    default_context = {
        "wishlist": "Add To Wishlist",
    }
    
    # Check user wishlist
    if request.user.is_authenticated: 
        isWishlisted = Wishlist.objects.filter(user=request.user).filter(auction=current_auction)
        if isWishlisted:
            default_context = {
                "wishlist": "Remove From Wishlist"
            }

    # Check if current auction is user's and replace wishlist button into close auction button
    if request.method == "GET" and isUserAuction(request.user, current_auction.pk):
        default_context = {
            "wishlist": "Remove From Wishlist",
            "closeButton": closeButton,
            "closeMessage": "Close Auction"
        }

    # POST REQUESTS
    if request.method == "POST":
        # For any POST request user is ask to login of register
        if not request.user.is_authenticated: 
            return render(request, "auctions/login.html")
        else:   
            # Add to wishlist
            if "wishlist" in request.POST and request.POST["wishlist"] == "Add To Wishlist":
                # Create wishlist item in model
                new_wishlist = Wishlist(
                    user = request.user,
                    auction = current_auction
                )
                new_wishlist.save()
                context = {
                    "message": "This item has been added to your wishlist !",
                    "wishlist": "Remove From Wishlist"
                }
            # Remove from wishlist
            elif "wishlist" in request.POST and request.POST["wishlist"] == "Remove From Wishlist":
                # Delete item from wishlist model
                isWishlisted.delete()
                context = {
                    "message": "This item has been removed from your wishlist !",
                    "wishlist": "Add To Wishlist"
                }
            #  Bid
            elif "bid" in request.POST:
                # Get bid informations from form
                bid_form = BidForm(request.POST)
                if bid_form.is_valid():
                    bid = bid_form.cleaned_data["bid"]
                    # Handle first bid 
                    if current_auction.bid_counter == 0 and bid < current_auction.bid:
                        context = {
                            "message": "Bid must be at least equal to starting bid",
                            "wishlist": default_context["wishlist"]
                        }
                    # Handle next bids
                    elif current_auction.bid_counter != 0 and bid <= current_auction.bid:
                        context = {
                            "message": "Bid must be higher than current bid",
                            "wishlist": default_context["wishlist"]
                        }
                    # Create bid in model
                    else: 
                        new_bid = Bid(
                            bidder = request.user,
                            auction = current_auction,
                            bid = bid,
                        )
                        new_bid.save()

                        current_auction.bid = bid
                        current_auction.bid_counter = Bid.objects.filter(auction=current_auction).count()
                        current_auction.save()

                        # For any bid placed, add item to wishlist 
                        new_wishlist = Wishlist(
                            user = request.user,
                            auction = current_auction
                        )
                        new_wishlist.save()

                        context = {
                            "message": "Bid placed !",
                            "wishlist": default_context["wishlist"]
                        }
            # Close auction
            elif "close" in request.POST:
                # Set auction to non-active
                current_auction.active = False
                current_auction.save()

                context = {
                    "message": "Bid Closed !",
                    "closeButton": closeButton,
                }
            
        return render(request, "auctions/auction.html", {
            "bid_form": bid_form,
            "auction": current_auction,
            "comment_form": comment_form,
            "images": images,
            "active": current_auction.active,
            "context": context
        })
        
    # GET REQUESTS
    return render(request, "auctions/auction.html", {
        "bid_form": bid_form,
        "auction": current_auction,
        "comment_form": comment_form,
        "images": images,
        "active": current_auction.active,
        "context": default_context
    })

        
def wishlist(request):
    # Get all wishlisted auctions by current user
    wishlist_items = Wishlist.objects.filter(user=request.user)
    # Get auctions images
    images = getFirstImage(ImagesUpload.objects.all())
    return render(request, "auctions/wishlist.html", {
        "wishlist": wishlist_items,
        "images": images
    })


def myAuctions(request):
    # Get all active auctions posted by current user
    myActiveAuctions = Auction.objects.filter(seller=request.user).filter(active=True)
    # Get all non-active auctions posted by current user
    myClosedAuctions = Auction.objects.filter(seller=request.user).filter(active=False)
        # Get auctions images
    images = getFirstImage(ImagesUpload.objects.all())

    return render(request, 'auctions/my_auctions.html', {
        "active": myActiveAuctions,
        "closed": myClosedAuctions,
        "images": images
    })
